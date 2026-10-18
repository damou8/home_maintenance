import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { HomeAssistant } from "custom-card-helpers";
import { formatDateNumeric } from "custom-card-helpers";

import { t } from "./strings";
import { HomeMaintenanceCardEditor } from "./home-maintenance-card-editor";

export interface HomeMaintenanceCardConfig {
    type: string;
    title?: string;
    show_disabled?: boolean;
    labels?: string[];
    warning_threshold?: number;
    tap_action?: Record<string, any>;
    hold_action?: Record<string, any>;
}

interface TaskItem {
    entity_id: string;
    name: string;
    icon: string;
    due: boolean;
    enabled: boolean;
    next?: Date;
    // Share of the interval left, 100 for a task without one
    pct: number;
    // Runtime limit: share of the hours left, and hours left
    runtimePct?: number;
    runtimeLeft?: number;
}

const DEFAULT_WARNING_THRESHOLD = 15;
const HOLD_DELAY_MS = 500;

// Same colors as Mushroom's red/blue/green
const COLORS = {
    due: "var(--red-color, #f44336)",
    soon: "var(--blue-color, #2196f3)",
    ok: "var(--green-color, #4caf50)",
    disabled: "var(--disabled-color, #bdbdbd)",
};

class HomeMaintenanceCard extends LitElement {
    @property({ attribute: false }) hass?: HomeAssistant;
    @state() private _config?: HomeMaintenanceCardConfig;

    private _holdTimer?: number;
    private _held = false;

    static getConfigElement() {
        return document.createElement("home-maintenance-card-editor");
    }

    static getStubConfig(): Omit<HomeMaintenanceCardConfig, "type"> {
        return {};
    }

    setConfig(config: HomeMaintenanceCardConfig) {
        if (!config) throw new Error("Invalid configuration");
        this._config = config;
    }

    getCardSize() {
        return Math.max(1, this._tasks().length);
    }

    // Take the whole width of a section, height follows the number of tasks
    getGridOptions() {
        return { columns: "full", min_columns: 6 };
    }

    private _tasks(): TaskItem[] {
        if (!this.hass || !this._config) return [];
        const hass = this.hass as any;
        const labels = this._config.labels ?? [];
        const showDisabled = this._config.show_disabled ?? false;
        const now = Date.now();

        const items: TaskItem[] = [];
        for (const entry of Object.values<any>(hass.entities ?? {})) {
            if (entry.platform !== "home_maintenance" || !entry.entity_id.startsWith("binary_sensor.")) continue;
            if (entry.hidden) continue;
            if (labels.length && !(entry.labels ?? []).some((l: string) => labels.includes(l))) continue;

            const stateObj = hass.states[entry.entity_id];
            if (!stateObj) continue;
            const attrs = stateObj.attributes;
            const enabled = attrs.enabled !== false;
            if (!enabled && !showDisabled) continue;

            // Share of the interval still left, 100% right after the task was done
            const last = Date.parse(attrs.last_performed);
            const next = Date.parse(attrs.next_due);
            let pct = 100;
            if (!isNaN(last) && !isNaN(next) && next > last) {
                pct = Math.min(100, Math.max(0, Math.trunc(((next - now) / (next - last)) * 100)));
            }

            const [y, m, d] = String(attrs.next_due ?? "").slice(0, 10).split("-").map(Number);
            const nextDate = y && m && d ? new Date(y, m - 1, d) : undefined;
            const hasRuntime = typeof attrs.runtime_remaining === "number";

            items.push({
                entity_id: entry.entity_id,
                name: this._taskName(entry, stateObj),
                icon: attrs.icon ?? "mdi:calendar-check",
                due: stateObj.state === "on",
                enabled,
                next: nextDate,
                pct,
                runtimePct: hasRuntime ? attrs.runtime_remaining : undefined,
                runtimeLeft: hasRuntime ? attrs.runtime_left : undefined,
            });
        }

        // Due first, then by next due date, then by name; disabled tasks last
        return items.sort((a, b) =>
            Number(b.enabled) - Number(a.enabled)
            || Number(b.due) - Number(a.due)
            || (a.next?.getTime() ?? Infinity) - (b.next?.getTime() ?? Infinity)
            || a.name.localeCompare(b.name)
        );
    }

    // Entity names are prefixed with the device name ("Home Maintenance ..."), drop it
    private _taskName(entry: any, stateObj: any): string {
        const name: string = stateObj.attributes.friendly_name ?? entry.entity_id;
        const device = (this.hass as any).devices?.[entry.device_id];
        const deviceName: string | undefined = device?.name_by_user ?? device?.name;
        if (deviceName && name.startsWith(`${deviceName} `)) {
            return name.slice(deviceName.length + 1);
        }
        return name;
    }

    private _color(task: TaskItem): string {
        if (!task.enabled) return COLORS.disabled;
        if (task.due) return COLORS.due;
        // Soon by date or by runtime, whichever is lower
        const pct = Math.min(task.pct, task.runtimePct ?? 100);
        if (pct <= (this._config?.warning_threshold ?? DEFAULT_WARNING_THRESHOLD)) return COLORS.soon;
        return COLORS.ok;
    }

    private _actionConfig(task: TaskItem) {
        const language = this.hass?.language;
        // Default tap: mark the task done, after a confirmation
        const tap = this._config?.tap_action ?? {
            action: "perform-action",
            perform_action: "home_maintenance.reset_last_performed",
            confirmation: { text: t(language, "confirm_complete") },
        };
        return {
            entity: task.entity_id,
            tap_action: this._withTarget(tap, task.entity_id),
            hold_action: this._withTarget(this._config?.hold_action ?? { action: "more-info" }, task.entity_id),
        };
    }

    // An action calling a service without a target applies to the tapped task
    private _withTarget(action: Record<string, any>, entityId: string) {
        if (!["perform-action", "call-service"].includes(action.action)) return action;
        if (action.target || action.data?.entity_id || action.service_data?.entity_id) return action;
        return { ...action, target: { entity_id: entityId } };
    }

    private _fireAction(task: TaskItem, action: "tap" | "hold") {
        this.dispatchEvent(new CustomEvent("hass-action", {
            detail: { config: this._actionConfig(task), action },
            bubbles: true,
            composed: true,
        }));
    }

    private _onPointerDown(task: TaskItem) {
        this._held = false;
        window.clearTimeout(this._holdTimer);
        this._holdTimer = window.setTimeout(() => {
            this._held = true;
            this._fireAction(task, "hold");
        }, HOLD_DELAY_MS);
    }

    private _onPointerUp() {
        window.clearTimeout(this._holdTimer);
    }

    private _onClick(task: TaskItem) {
        if (this._held) {
            this._held = false;
            return;
        }
        this._fireAction(task, "tap");
    }

    private _onKeyDown(ev: KeyboardEvent, task: TaskItem) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            this._fireAction(task, "tap");
        }
    }

    render() {
        if (!this.hass || !this._config) return nothing;
        const tasks = this._tasks();
        const language = this.hass.language;

        return html`
            ${this._config.title ? html`<div class="title">${this._config.title}</div>` : nothing}
            ${tasks.length === 0
                ? html`<ha-card class="empty">${t(language, "no_tasks")}</ha-card>`
                : html`
                    <div class="tasks">
                        ${tasks.map((task) => this._renderTask(task))}
                    </div>
                `}
        `;
    }

    // Date tasks show the next due date, runtime tasks the share of hours left
    private _secondary(task: TaskItem): string {
        const language = this.hass!.language;
        const date = task.next ? formatDateNumeric(task.next, (this.hass as any).locale) : t(language, "unknown");
        if (task.runtimePct === undefined) return t(language, "next", { date, pct: task.pct });
        if (!task.next) return t(language, "runtime", { pct: task.runtimePct, hours: task.runtimeLeft ?? 0 });
        return t(language, "next_runtime", { date, pct: task.runtimePct });
    }

    private _renderTask(task: TaskItem) {
        return html`
            <ha-card
                class="task ${task.enabled ? "" : "disabled"}"
                tabindex="0"
                role="button"
                @click=${() => this._onClick(task)}
                @pointerdown=${() => this._onPointerDown(task)}
                @pointerup=${this._onPointerUp}
                @pointerleave=${this._onPointerUp}
                @pointercancel=${this._onPointerUp}
                @contextmenu=${(ev: Event) => ev.preventDefault()}
                @keydown=${(ev: KeyboardEvent) => this._onKeyDown(ev, task)}
            >
                <div class="container">
                    <div class="icon ${task.due && task.enabled ? "pulse" : ""}" style="--icon-color: ${this._color(task)}">
                        <ha-icon .icon=${task.icon}></ha-icon>
                    </div>
                    <div class="info">
                        <span class="primary">${task.name}</span>
                        <span class="secondary">${this._secondary(task)}</span>
                    </div>
                </div>
            </ha-card>
        `;
    }

    static styles = css`
        :host {
            display: block;
        }
        .title {
            font-size: var(--ha-card-header-font-size, 24px);
            font-weight: var(--ha-font-weight-normal, 400);
            color: var(--ha-card-header-color, var(--primary-text-color));
            padding: 4px 4px 8px;
        }
        .tasks {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(var(--home-maintenance-card-min-width, 300px), 1fr));
            gap: var(--grid-card-gap, 8px);
        }
        ha-card {
            cursor: pointer;
            user-select: none;
            -webkit-tap-highlight-color: transparent;
        }
        ha-card:focus-visible {
            outline: 2px solid var(--primary-color);
            outline-offset: 2px;
        }
        ha-card.empty {
            padding: 12px;
            cursor: default;
            color: var(--secondary-text-color);
        }
        ha-card.disabled .info {
            opacity: 0.6;
        }
        .task {
            height: 56px;
            box-sizing: border-box;
        }
        .container {
            display: flex;
            align-items: center;
            gap: 10px;
            height: 100%;
            padding: 0 10px;
            box-sizing: border-box;
        }
        .icon {
            flex: none;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            margin: 6px 0;
            border-radius: 50%;
            color: var(--icon-color);
            --mdc-icon-size: 24px;
        }
        .icon.pulse {
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.2); opacity: 0.6; }
            100% { transform: scale(1); opacity: 1; }
        }
        .info {
            display: flex;
            flex-direction: column;
            min-width: 0;
        }
        .primary {
            font-size: 14px;
            font-weight: var(--ha-font-weight-medium, 500);
            line-height: 22.4px;
            letter-spacing: 0.1px;
            color: var(--primary-text-color);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .secondary {
            font-size: 12px;
            font-weight: var(--ha-font-weight-normal, 400);
            line-height: 14.4px;
            letter-spacing: 0.4px;
            color: var(--primary-text-color);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
    `;
}

// This script can run before Home Assistant's app starts, and the app then
// swaps in a scoped custom element registry that forgets anything defined
// earlier: wait for the app's root element before defining the card.
Promise.race([
    customElements.whenDefined("home-assistant"),
    customElements.whenDefined("hc-main"),
]).then(() => {
    if (customElements.get("home-maintenance-card")) return;
    customElements.define("home-maintenance-card", HomeMaintenanceCard);
    customElements.define("home-maintenance-card-editor", HomeMaintenanceCardEditor);
    const language = document.documentElement.lang;
    (window as any).customCards = (window as any).customCards || [];
    (window as any).customCards.push({
        type: "home-maintenance-card",
        name: t(language, "card_name"),
        description: t(language, "card_description"),
        preview: true,
    });
});
