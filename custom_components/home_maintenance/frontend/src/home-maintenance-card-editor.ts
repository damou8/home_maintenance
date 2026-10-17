import { LitElement, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";
import type { HomeAssistant } from "custom-card-helpers";

import { t } from "./strings";
import type { HomeMaintenanceCardConfig } from "./home-maintenance-card";

const SCHEMA = [
    { name: "title", selector: { text: {} } },
    { name: "show_disabled", selector: { boolean: {} } },
    { name: "labels", selector: { label: { multiple: true } } },
    { name: "warning_threshold", selector: { number: { min: 0, max: 100, mode: "box", unit_of_measurement: "%" } } },
    { name: "tap_action", selector: { ui_action: {} } },
    { name: "hold_action", selector: { ui_action: {} } },
];

export class HomeMaintenanceCardEditor extends LitElement {
    @property({ attribute: false }) hass?: HomeAssistant;
    @state() private _config?: HomeMaintenanceCardConfig;

    setConfig(config: HomeMaintenanceCardConfig) {
        this._config = config;
    }

    render() {
        if (!this.hass || !this._config) return nothing;
        return html`
            <ha-form
                .hass=${this.hass}
                .data=${this._config}
                .schema=${SCHEMA}
                .computeLabel=${(schema: { name: string }) => t(this.hass!.language, schema.name)}
                @value-changed=${this._valueChanged}
            ></ha-form>
        `;
    }

    private _valueChanged(ev: CustomEvent) {
        const config = { ...ev.detail.value };
        // Keep the YAML short: drop options left empty
        for (const key of Object.keys(config)) {
            if (config[key] === "" || config[key] === undefined || (Array.isArray(config[key]) && !config[key].length)) {
                delete config[key];
            }
        }
        this.dispatchEvent(new CustomEvent("config-changed", {
            detail: { config },
            bubbles: true,
            composed: true,
        }));
    }
}
