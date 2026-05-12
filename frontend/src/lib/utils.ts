import clsx, { type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} МБ`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} ГБ`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function categoryLabel(c: string | null | undefined): string {
  switch (c) {
    case "strict":
      return "Строго конфиденциально";
    case "confidential":
      return "Конфиденциально";
    case "internal":
      return "Для внутреннего использования";
    case "public":
      return "Публичный";
    default:
      return "—";
  }
}

export function categoryColor(c: string | null | undefined): string {
  switch (c) {
    case "strict":
      return "bg-red-100 text-red-700";
    case "confidential":
      return "bg-orange-100 text-orange-700";
    case "internal":
      return "bg-yellow-100 text-yellow-700";
    case "public":
      return "bg-green-100 text-green-700";
    default:
      return "bg-slate-100 text-slate-600";
  }
}

export function findingTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    passport: "Паспорт",
    snils: "СНИЛС",
    inn_person: "ИНН (физ. лицо)",
    inn_org: "ИНН (организация)",
    bank_card: "Банковская карта",
    phone: "Телефон",
    email: "Email",
    date_of_birth: "Дата рождения",
    oms_policy: "Полис ОМС",
    driver_license: "Водительское удостоверение",
    fio: "ФИО",
    address: "Адрес",
  };
  return labels[type] ?? type;
}

export function statusLabel(s: string): string {
  const labels: Record<string, string> = {
    queued: "В очереди",
    processing: "Обработка",
    completed: "Готово",
    failed: "Ошибка",
  };
  return labels[s] ?? s;
}

export function statusColor(s: string): string {
  switch (s) {
    case "completed":
      return "bg-green-100 text-green-700";
    case "processing":
      return "bg-blue-100 text-blue-700";
    case "queued":
      return "bg-slate-100 text-slate-600";
    case "failed":
      return "bg-red-100 text-red-700";
    default:
      return "bg-slate-100 text-slate-600";
  }
}
