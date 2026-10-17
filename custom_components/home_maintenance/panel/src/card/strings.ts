// Strings for the dashboard card, which is loaded on every dashboard and
// kept separate from the panel's translations to stay small.
const STRINGS: Record<string, Record<string, string>> = {
    en: {
        next: "Next: {date} ({pct}%)",
        unknown: "Unknown",
        confirm_complete: "Do you really want to mark this task as done?",
        no_tasks: "No tasks",
        card_name: "Home Maintenance",
        card_description: "Your maintenance tasks, colored by how soon they are due.",
        title: "Title",
        show_disabled: "Show disabled tasks",
        labels: "Only tasks with these labels",
        warning_threshold: "Blue below (% of interval left)",
        tap_action: "Tap action",
        hold_action: "Hold action",
    },
    fr: {
        next: "Prochain : {date} ({pct}%)",
        unknown: "Inconnue",
        confirm_complete: "Voulez-vous vraiment marquer cette tâche comme effectuée ?",
        no_tasks: "Aucune tâche",
        card_name: "Home Maintenance",
        card_description: "Vos tâches de maintenance, colorées selon leur échéance.",
        title: "Titre",
        show_disabled: "Afficher les tâches désactivées",
        labels: "Uniquement les tâches avec ces étiquettes",
        warning_threshold: "Bleu en dessous de (% d'intervalle restant)",
        tap_action: "Action au toucher",
        hold_action: "Action en maintenant",
    },
    de: {
        next: "Nächste: {date} ({pct} %)",
        unknown: "Unbekannt",
        confirm_complete: "Möchtest du diese Aufgabe wirklich als erledigt markieren?",
        no_tasks: "Keine Aufgaben",
        card_name: "Home Maintenance",
        card_description: "Deine Wartungsaufgaben, eingefärbt nach Fälligkeit.",
        title: "Titel",
        show_disabled: "Deaktivierte Aufgaben anzeigen",
        labels: "Nur Aufgaben mit diesen Labels",
        warning_threshold: "Blau unter (% verbleibendes Intervall)",
        tap_action: "Aktion beim Tippen",
        hold_action: "Aktion beim Halten",
    },
};

export function t(language: string | undefined, key: string, args: Record<string, string | number> = {}): string {
    const lang = (language ?? "en").split("-")[0];
    const text = STRINGS[lang]?.[key] ?? STRINGS.en[key] ?? key;
    return text.replace(/\{(\w+)\}/g, (_, name) => String(args[name] ?? ""));
}
