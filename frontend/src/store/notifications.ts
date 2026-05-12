import { create } from "zustand";

export type ToastType = "success" | "error" | "info" | "warning";

export interface Toast {
  id: number;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface NotificationState {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: number) => void;
}

let nextId = 1;

export const useNotificationStore = create<NotificationState>((set, get) => ({
  toasts: [],
  addToast: (toast) => {
    const id = nextId++;
    set((state) => ({ toasts: [...state.toasts, { ...toast, id }] }));
    const duration = toast.duration ?? 5000;
    setTimeout(() => get().removeToast(id), duration);
  },
  removeToast: (id) =>
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));

export function toast(t: Omit<Toast, "id">) {
  useNotificationStore.getState().addToast(t);
}
