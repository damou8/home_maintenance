import { css } from 'lit';

export const commonStyle = css`
    :host {
        color: var(--primary-text-color);
        background: var(--lovelace-background, var(--primary-background-color));
    }

    .header {
        background-color: var(--app-header-background-color);
        color: var(--app-header-text-color, white);
        border-bottom: var(--app-header-border-bottom, none);
    }

    .toolbar {
        height: var(--header-height);
        display: flex;
        align-items: center;
        font-size: 20px;
        padding: 0 16px;
        font-weight: 400;
        box-sizing: border-box;
    }

    .main-title {
        margin: 0 0 0 24px;
        line-height: 20px;
        flex-grow: 1;
    }

    .version {
        font-size: 14px;
        font-weight: 500;
        color: rgba(var(--rgb-text-primary-color), 0.9);
    }

    .view {
        height: calc(100vh - 65px);
        display: flex;
        align-content: start;
        justify-content: center;
        flex-wrap: wrap;
        align-items: flex-start;
    }

    ha-card {
        display: block;
        margin: 5px;
    }

    .card-new {
        width: 500px;
        max-width: 500px;
    }

    .card-current {
        width: 850px;
        max-width: 850px;
    }

    ha-expansion-panel {
        --input-fill-color: none;
    }

    .form-field {
        text-align: right;
        min-width: 265px;
    }

    .extras-panel {
        margin-bottom: 14px;
    }

    @media (max-width: 600px) {
        .form-field {
            width: 100%;
        }
    }
`;
