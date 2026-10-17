import {
    mdiCheckCircleOutline,
} from "@mdi/js";
import { LitElement, html, nothing } from "lit";
import { property, state, query } from "lit/decorators.js";
import type { HomeAssistant } from "custom-card-helpers";
import { formatDateNumeric } from "custom-card-helpers";

import { localize } from '../localize/localize';
import { VERSION } from "./const";
import { loadConfigDashboard } from "./helpers";
import { commonStyle } from './styles'
import { EntityRegistryEntry, IntegrationConfig, IntervalType, INTERVAL_TYPES, getIntervalTypeLabels, Label, NOTIFY_MODES, NotifyMode, Task, Tag } from './types';
import { completeTask, getConfig, loadLabelRegistry, loadRegistryEntries, loadTags, loadTask, loadTasks, removeTask, saveTask, updateTask } from './data/websockets';
import './components/hm-task-menu'

interface TaskFormData {
    title: string;
    interval_value: number | "";
    interval_type: string;
    last_performed: string;
    icon: string;
    label: string[];
    tag: string;
    notify_mode: NotifyMode;
    notify_targets: string[];
}

// Table cells render inside ha-data-table's shadow root, so they are styled inline
const STATUS_ICON_STYLE = "--mdc-icon-size: 18px; color: var(--secondary-text-color); margin-left: 4px;";

const emptyFormData = (): TaskFormData => ({
    title: "",
    interval_value: "",
    interval_type: "days",
    last_performed: "",
    icon: "",
    label: [],
    tag: "",
    notify_mode: "default",
    notify_targets: [],
});

export class HomeMaintenancePanel extends LitElement {
    @property() hass?: HomeAssistant;
    @property() narrow!: boolean;

    @state() private tags: Tag[] | null = null;
    @state() private tasks: Task[] = [];
    @state() private config: IntegrationConfig | null = null;
    @state() private registry: EntityRegistryEntry[] = [];
    @state() private labelRegistry: Label[] = [];

    // New Task form state
    @state() private _formData: TaskFormData = emptyFormData();
    private _advancedOpen: boolean = false;

    // Edit dialog state
    @state() private _editingTaskId: string | null = null;
    @state() private _editFormData: TaskFormData = emptyFormData();

    private get _columns() {
        return {
            icon: {
                title: "",
                moveable: false,
                showNarrow: false,
                label: "icon",
                type: "icon",
                template: (task: any) =>
                    task.icon ? html`<ha-icon style=${task.enabled ? "" : "opacity: 0.4;"} .icon=${task.icon}></ha-icon>` : nothing,
            },
            tagIcon: {
                title: "",
                moveable: false,
                showNarrow: false,
                label: "tag",
                type: "icon",
                template: (task: any) =>
                    task.tagIcon ? html`<ha-icon .icon=${task.tagIcon}></ha-icon>` : nothing,
            },
            title: {
                title: 'Title',
                main: true,
                showNarrow: true,
                sortable: true,
                filterable: true,
                grows: true,
                extraTemplate: (task: any) => {
                    const entity = this.registry.find((entry) => entry.unique_id === task.id);
                    const labels = entity
                        ? this.labelRegistry.filter((lr) => entity.labels.includes(lr.label_id))
                        : [];

                    return html`
                        ${!task.enabled
                            ? html`<ha-icon style=${STATUS_ICON_STYLE} icon="mdi:pause-circle-outline"
                                title=${localize('panel.cards.current.disabled', this.hass!.language)}></ha-icon>`
                            : nothing}
                        ${task.enabled && task.notify_mode === "none"
                            ? html`<ha-icon style=${STATUS_ICON_STYLE} icon="mdi:bell-off-outline"
                                title=${localize('notify_modes.none', this.hass!.language)}></ha-icon>`
                            : nothing}
                        ${labels.length
                            ? html`<ha-data-table-labels .labels=${labels}></ha-data-table-labels>`
                            : nothing}
                    `;
                },
            },
            interval_days: {
                title: 'Interval',
                showNarrow: false,
                sortable: true,
                minWidth: "100px",
                maxWidth: "100px",
                template: (task: Task) => {
                    const type = task.interval_type;
                    const isSingular = task.interval_value === 1;
                    const labelKey = isSingular ? type.slice(0, -1) : type;
                    return `${task.interval_value} ${localize(`intervals.${labelKey}`, this.hass!.language)}`;
                }
            },
            last_performed: {
                title: 'Last Performed',
                showNarrow: false,
                sortable: true,
                minWidth: "150px",
                maxWidth: "150px",
                template: (task: Task) => {
                    if (!task.last_performed) return "-";

                    const date = new Date(this.computeISODate(task.last_performed));
                    return formatDateNumeric(date, this.hass!.locale);
                }
            },
            next_due: {
                title: localize('panel.cards.current.next', this.hass!.language),
                showNarrow: true,
                sortable: true,
                direction: "asc",
                minWidth: "100px",
                maxWidth: "100px",
                template: (task: any) => {
                    const now = new Date();
                    const next = new Date(task.next_due);
                    const isDue = next <= now;
                    const style = !task.enabled
                        ? "opacity: 0.5;"
                        : isDue ? "color: var(--error-color, red); font-weight: bold;" : "";

                    return html`
                        <span style=${style}>
                            ${formatDateNumeric(next, this.hass!.locale)}
                        </span>` || "—";
                },
            },
            complete: {
                minWidth: "64px",
                maxWidth: "64px",
                sortable: false,
                groupable: false,
                showNarrow: true,
                moveable: false,
                hideable: false,
                type: "overflow",
                template: (task: Task) => html`
                <ha-icon-button
                    @click=${() => this._handleCompleteTaskClick(task.id)}
                    .label="Complete"
                    title="Mark Task Complete"
                    .path=${mdiCheckCircleOutline}
                ></ha-icon-button>
              `,
            },
            actions: {
                title: "",
                label: "actions",
                showNarrow: true,
                moveable: false,
                hideable: false,
                type: "overflow-menu",
                template: (task: any) => html`
                    <hm-task-menu
                        .hass=${this.hass}
                        .items=${[
                        {
                            value: 'edit',
                            label: localize('panel.cards.current.actions.edit', this.hass!.language),
                            icon: 'mdi:pencil'
                        },
                        task.enabled
                            ? {
                                value: 'disable',
                                label: localize('panel.cards.current.actions.disable', this.hass!.language),
                                icon: 'mdi:pause-circle-outline'
                            }
                            : {
                                value: 'enable',
                                label: localize('panel.cards.current.actions.enable', this.hass!.language),
                                icon: 'mdi:play-circle-outline'
                            },
                        {
                            value: 'delete',
                            label: localize('panel.cards.current.actions.remove', this.hass!.language),
                            icon: 'mdi:delete'
                        }
                    ]}
                    @menu-action=${(e: CustomEvent) => this._handleMenuAction(e, task.id)}
                    ></hm-task-menu>
                `,
            },
        }
    };

    // ha-data-table re-processes its rows whenever it gets a new columns/data reference,
    // so both are cached and only rebuilt when their inputs change.
    private _columnsCache?: { key: string; columns: Record<string, any> };
    private _rowsCache?: { tasks: Task[]; rows: any[] };

    private get _columnsToDisplay() {
        const key = `${this.narrow}|${this.hass!.language}`;
        if (this._columnsCache?.key !== key) {
            const columns = Object.fromEntries(
                Object.entries(this._columns).filter(([_, col]) =>
                    this.narrow ? col.showNarrow !== false : true
                )
            );
            this._columnsCache = { key, columns };
        }
        return this._columnsCache.columns;
    }

    private get _rows() {
        if (this._rowsCache?.tasks !== this.tasks) {
            this._rowsCache = { tasks: this.tasks, rows: this._computeRows(this.tasks) };
        }
        return this._rowsCache.rows;
    }

    private _computeRows(tasks: Task[]) {
        return tasks.map((task: Task) => ({
            icon: task.icon,
            id: task.id,
            title: task.title,
            interval_value: task.interval_value,
            interval_type: task.interval_type,
            last_performed: task.last_performed ?? 'Never',
            interval_days: (() => {
                switch (task.interval_type) {
                    case "days":
                        return task.interval_value;
                    case "weeks":
                        return task.interval_value * 7;
                    case "months":
                        return task.interval_value * 30;
                    default:
                        return Number.MAX_SAFE_INTEGER;
                }
            })(),
            next_due: (() => {
                const [datePart] = task.last_performed.split("T");
                const [year, month, day] = datePart.split("-").map(Number);
                const next = new Date(year, month - 1, day);

                switch (task.interval_type) {
                    case "days":
                        next.setDate(next.getDate() + task.interval_value);
                        break;
                    case "weeks":
                        next.setDate(next.getDate() + task.interval_value * 7);
                        break;
                    case "months":
                        next.setMonth(next.getMonth() + task.interval_value);
                        break;
                    default:
                        throw new Error(`Unsupported interval type: ${task.interval_type}`);
                }

                return next;
            })(),
            tagIcon: (() => task.tag_id && task.tag_id.trim() !== "" ? "mdi:tag" : undefined)(),
            enabled: task.enabled !== false,
            notify_mode: task.notify_mode ?? "default",
        }));
    }

    private get _basicSchema() {
        return [
            { name: "title", required: true, selector: { text: {} }, },
            { name: "interval_value", required: true, selector: { number: { min: 1, mode: "box" } }, },
            {
                name: "interval_type",
                required: true,
                selector: {
                    select: {
                        options: INTERVAL_TYPES.map((type) => ({
                            value: type,
                            label: getIntervalTypeLabels(this.hass!.language)[type],
                        })),
                        mode: "dropdown"
                    },
                },
            },
        ]
    };

    private get _advancedSchema() {
        return [
            { name: "last_performed", selector: { date: {} }, },
            { name: "icon", selector: { icon: {} }, },
            { name: "label", selector: { label: { multiple: true } }, },
            { name: "tag", selector: { entity: { filter: { domain: "tag" } } }, },
            ...this._notifySchema(this._formData),
        ]
    };

    // Targets are only asked for when the task overrides the default ones
    private _notifySchema(data: TaskFormData) {
        return [
            {
                name: "notify_mode",
                required: true,
                selector: {
                    select: {
                        options: NOTIFY_MODES.map((mode) => ({
                            value: mode,
                            label: localize(`notify_modes.${mode}`, this.hass!.language),
                        })),
                        mode: "dropdown",
                    },
                },
            },
            ...(data.notify_mode === "custom"
                ? [{ name: "notify_targets", selector: { entity: { filter: { domain: "notify" }, multiple: true } } }]
                : []),
        ];
    }

    // Helper under the notification field: who gets notified by default
    private get _defaultTargetsHelper(): string {
        const targets: string[] = this.config?.options.notify_targets ?? [];
        if (!targets.length) {
            return localize('panel.notify.no_default_targets', this.hass!.language);
        }
        const names = targets
            .map((id) => this.hass!.states[id]?.attributes.friendly_name ?? id)
            .join(", ");
        return localize('panel.notify.default_targets', this.hass!.language, '{targets}', names);
    }

    private get _editSchema() {
        return [
            { name: "interval_value", required: true, selector: { number: { min: 1, mode: "box" } }, },
            {
                name: "interval_type",
                required: true,
                selector: {
                    select: {
                        options: INTERVAL_TYPES.map((type) => ({
                            value: type,
                            label: getIntervalTypeLabels(this.hass!.language)[type],
                        })),
                        mode: "dropdown"
                    },
                },
            },
            { type: "constant", name: localize('panel.dialog.edit_task.sections.optional', this.hass!.language), disabled: true },
            { name: "last_performed", selector: { date: {} }, },
            { name: "icon", selector: { icon: {} }, },
            { name: "label", selector: { label: { multiple: true } }, },
            { name: "tag", selector: { entity: { filter: { domain: "tag" } } }, },
            ...this._notifySchema(this._editFormData),
        ]
    };

    private _computeLabel = (schema: { name: string }): string => {
        try {
            return localize(`panel.cards.new.fields.${schema.name}.heading`, this.hass!.language) ?? schema.name;
        } catch {
            return schema.name;
        }
    }

    private _computeHelper = (schema: { name: string }): string => {
        if (schema.name === "notify_mode") {
            return this._formData.notify_mode === "default" ? this._defaultTargetsHelper : "";
        }
        try {
            return localize(`panel.cards.new.fields.${schema.name}.helper`, this.hass!.language) ?? "";
        } catch {
            return "";
        }
    }

    private _computeEditLabel = (schema: { name: string }): string => {
        try {
            return localize(`panel.dialog.edit_task.fields.${schema.name}.heading`, this.hass!.language) ?? schema.name;
        } catch {
            return schema.name;
        }
    }

    private _computeEditHelper = (schema: { name: string }): string => {
        if (schema.name === "notify_mode") {
            return this._editFormData.notify_mode === "default" ? this._defaultTargetsHelper : "";
        }
        try {
            return localize(`panel.dialog.edit_task.fields.${schema.name}.helper`, this.hass!.language) ?? "";
        } catch {
            return "";
        }
    }

    private async connect() {
        await loadConfigDashboard();
        this.config = await getConfig(this.hass!);
        await this.loadData();
    }

    private async loadData() {
        // Fetch everything first, then assign in one go so the table renders once with complete data
        const [tags, tasks, registry, labelRegistry] = await Promise.all([
            loadTags(this.hass!),
            loadTasks(this.hass!),
            loadRegistryEntries(this.hass!),
            loadLabelRegistry(this.hass!),
        ]);
        this.registry = registry;
        this.labelRegistry = labelRegistry;
        this.tags = tags;
        this.tasks = tasks;
    }

    private async resetForm() {
        this._formData = emptyFormData();

        await this.loadData();
    }

    private async resetEditForm() {
        this._editFormData = emptyFormData();
    }

    private computeISODate(dateStr: string): string {
        let isoDateStr: string;

        if (dateStr) {
            // Only take the YYYY-MM-DD part to avoid time zone issues
            const [yearStr, monthStr, dayStr] = dateStr.split("T")[0].split("-");
            const year = Number(yearStr);
            const month = Number(monthStr);
            const day = Number(dayStr);

            if (!isNaN(year) && !isNaN(month) && !isNaN(day)) {
                const parsedDate = new Date(year, month - 1, day);
                parsedDate.setHours(0, 0, 0, 0);
                isoDateStr = parsedDate.toISOString();
            } else {
                alert("Invalid date entered.");
                const fallback = new Date();
                fallback.setHours(0, 0, 0, 0);
                isoDateStr = fallback.toISOString();
            }
        } else {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            isoDateStr = today.toISOString();
        }

        return isoDateStr;
    }

    connectedCallback() {
        super.connectedCallback();
        this.connect();
    }

    render() {
        if (!this.hass) return html``;

        if (!this.tasks || !this.tags) {
            return html`<p>${localize('common.loading', this.hass.language)}</p>`;
        }

        return html`
            <div class="header">
                <div class="toolbar">
                    <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
                    <div class="main-title">
                        ${this.config?.options.sidebar_title}
                    </div>
                    <div class="version">
                        v${VERSION}
                    </div>
                </div>
            </div>

            <div class="view">
                <ha-card
                    header="${localize('panel.cards.new.title', this.hass.language)}"
                    class="card-new"
                >
                    <div class="card-content">${this.renderForm()}</div>
                </ha-card>

                <ha-card
                    header="${localize('panel.cards.current.title', this.hass.language)}"
                    class="card-current"
                >
                    <div class="card-content">${this.renderTasks()}</div>
                </ha-card>
            </div>

            ${this.renderEditDialog()}
        `;
    }

    renderForm() {
        if (!this.hass) return html``;

        return html`
            <ha-form
                .hass=${this.hass}
                .schema=${this._basicSchema}
                .computeLabel=${this._computeLabel.bind(this)}
                .computeHelper=${this._computeHelper.bind(this)}
                .data=${this._formData}
                @value-changed=${(e: CustomEvent) => this._handleFormValueChanged(e)}
            ></ha-form>

            <ha-expansion-panel
                header="${localize('panel.cards.new.sections.optional', this.hass.language)}"
                .opened=${this._advancedOpen}
                @opened-changed=${(e: CustomEvent) => (this._advancedOpen = e.detail.value)}
                class="extras-panel"
            >
                <ha-form
                    .hass=${this.hass}
                    .data=${this._formData}
                    .schema=${this._advancedSchema}
                    .computeLabel=${this._computeLabel.bind(this)}
                    .computeHelper=${this._computeHelper.bind(this)}
                    @value-changed=${(e: CustomEvent) => this._handleFormValueChanged(e)}
                ></ha-form>
            </ha-expansion-panel>

            <div class="form-field">
                <ha-button size="small" class="add-button"
                    @click=${this._handleAddTaskClick}>${localize('panel.cards.new.actions.add_task', this.hass.language)}
                </ha-button>
            </div>
        `;
    }

    renderTasks() {
        if (!this.hass) return html``;

        if (!this.tasks || this.tasks.length === 0) {
            return html`<span>${localize('common.no_tasks', this.hass!.language)}</span>`;
        }

        return html`
            <div class="table-wrapper">
                <ha-data-table
                    .hass=${this.hass}
                    .columns=${this._columnsToDisplay}
                    .data=${this._rows}
                    .narrow=${this.narrow}
                    auto-height
                    id="tasks-table"
                    class="tasks-table"
                    clickable
                >
                </ha-data-table>
            </div>
        `;
    }

    renderEditDialog() {
        if (!this.hass) return html``;

        if (!this._editingTaskId) return html``;

        return html`
            <ha-dialog
                open
                header-title="${localize('panel.dialog.edit_task.title', this.hass.language)}: ${this._editFormData.title}"
                prevent-scrim-close
                @closed=${this._handleDialogClosed}
            >
                <ha-form
                    autofocus
                    .hass=${this.hass}
                    .schema=${this._editSchema}
                    .computeLabel=${this._computeEditLabel.bind(this)}
                    .computeHelper=${this._computeEditHelper.bind(this)}
                    .data=${this._editFormData}
                    @value-changed=${(e: CustomEvent) => this._handleEditFormValueChanged(e)}
                ></ha-form>

                <ha-dialog-footer slot="footer">
                    <ha-button data-dialog="close" appearance="plain" slot="secondaryAction">
                        ${localize('panel.dialog.edit_task.actions.cancel', this.hass.language)}
                    </ha-button>
                    <ha-button slot="primaryAction" @click=${this._handleSaveEditClick}>
                        ${localize('panel.dialog.edit_task.actions.save', this.hass.language)}
                    </ha-button>
                </ha-dialog-footer>
            </ha-dialog>
        `;
    }

    private async _handleAddTaskClick() {
        const { title, interval_value, interval_type, last_performed, tag, icon, label, notify_mode, notify_targets } = this._formData;

        if (!title?.trim() || !interval_value || !interval_type) {
            const msg = localize("panel.cards.new.alerts.required", this.hass!.language);
            alert(msg);
            return;
        }

        const payload: Record<string, any> = {
            title: title.trim(),
            interval_value,
            interval_type,
            last_performed: this.computeISODate(last_performed),
            tag_id: tag?.trim() || undefined,
            icon: icon?.trim() || "mdi:calendar-check",
            labels: label ?? [],
            notify_mode,
            notify_targets: notify_mode === "custom" ? notify_targets ?? [] : [],
        };

        try {
            await saveTask(this.hass!, payload);
            await this.resetForm();
        } catch (error) {
            console.error("Failed to add task:", error);
            const msg = localize('panel.cards.new.alerts.error', this.hass!.language)
            alert(msg);
        }
    };

    private async _handleCompleteTaskClick(id: string) {
        try {
            await completeTask(this.hass!, id);
            await this.loadData();
        } catch (e) {
            console.error("Failed to complete task:", e);
        }
    }

    private async _handleOpenEditDialogClick(id: string) {
        try {
            const task: Task = await loadTask(this.hass!, id);
            this._editingTaskId = task.id;
            let labels: Label[] = [];
            const entity = this.registry.find((entry) => entry.unique_id === task.id);
            if (entity)
                labels = this.labelRegistry.filter((lr) => entity.labels.includes(lr.label_id));

            this._editFormData = {
                title: task.title,
                interval_value: task.interval_value,
                interval_type: task.interval_type,
                last_performed: task.last_performed ?? "",
                icon: task.icon ?? "",
                label: labels.map((l) => l.label_id),
                tag: task.tag_id ?? "",
                notify_mode: task.notify_mode ?? "default",
                notify_targets: task.notify_targets ?? [],
            };

            await this.updateComplete;
        } catch (e) {
            console.error("Failed to fetch task for edit:", e);
        }
    }

    private async _handleSaveEditClick() {
        if (!this._editingTaskId) return;

        const lastPerformedISO = this.computeISODate(this._editFormData.last_performed);
        if (!lastPerformedISO) return;

        const updates: Record<string, any> = {
            title: this._editFormData.title.trim(),
            interval_value: Number(this._editFormData.interval_value),
            interval_type: this._editFormData.interval_type,
            last_performed: lastPerformedISO,
            icon: this._editFormData.icon?.trim() || "mdi:calendar-check",
            labels: this._editFormData.label,
            notify_mode: this._editFormData.notify_mode,
            notify_targets: this._editFormData.notify_mode === "custom" ? this._editFormData.notify_targets ?? [] : [],
        };

        if (this._editFormData.tag && this._editFormData.tag.trim() !== "") {
            updates.tag_id = this._editFormData.tag.trim();
        } else {
            updates.tag_id = null;
        }

        const payload = {
            task_id: this._editingTaskId,
            updates,
        };

        try {
            await updateTask(this.hass!, payload);
            this._editingTaskId = null;
            await this.resetEditForm();
            await this.loadData();
        } catch (e) {
            console.error("Failed to update task:", e);
        }
    }

    private async _handleRemoveTaskClick(id: string) {
        const msg = localize('panel.cards.current.confirm_remove', this.hass!.language)
        if (!confirm(msg)) return;
        try {
            await removeTask(this.hass!, id);
            await this.loadData();
        } catch (e) {
            console.error("Failed to remove task:", e);
        }
    }

    private _handleDialogClosed(e: CustomEvent) {
        // Ignore "closed" events bubbling up from components inside the dialog
        if (e.target !== e.currentTarget) return;
        this._editingTaskId = null;
    }

    private _handleMenuAction(e: CustomEvent, taskId: string) {
        const action = e.detail.action;
        switch (action) {
            case 'edit':
                this._handleOpenEditDialogClick(taskId);
                break;
            case 'disable':
            case 'enable':
                this._handleSetEnabledClick(taskId, action === 'enable');
                break;
            case 'delete':
                this._handleRemoveTaskClick(taskId);
                break;
        }
    }

    private async _handleSetEnabledClick(id: string, enabled: boolean) {
        try {
            await updateTask(this.hass!, { task_id: id, updates: { enabled } });
            await this.loadData();
        } catch (e) {
            console.error("Failed to change task state:", e);
        }
    }

    private _handleFormValueChanged(ev: CustomEvent) {
        this._formData = { ...this._formData, ...ev.detail.value };
    }

    private _handleEditFormValueChanged(ev: CustomEvent) {
        this._editFormData = { ...this._editFormData, ...ev.detail.value };
    }

    static styles = commonStyle;
}

customElements.define("home-maintenance-panel", HomeMaintenancePanel);
