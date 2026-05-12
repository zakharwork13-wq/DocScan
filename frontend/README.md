# DocScan Frontend

React + TypeScript + Vite фронтенд для системы поиска персональных данных.

## Стек

- **React 18** + **TypeScript 5**
- **Vite** — dev-сервер с HMR
- **Tailwind CSS** — стили
- **React Router 6** — роутинг
- **TanStack Query** — кеш API
- **Zustand** — глобальное состояние
- **Axios** — HTTP-клиент с авто-refresh JWT
- **Lucide React** — иконки

## Запуск

```bash
npm install
npm run dev          # http://localhost:5173
```

Vite автоматически проксирует `/api/*` на `http://localhost:8000` (см. `vite.config.ts`).

## Сборка

```bash
npm run build        # → dist/
npm run preview      # локальный просмотр сборки
```

## Структура

```
src/
├── api/           # axios клиенты по разделам (auth, scans, users, ...)
├── components/    # переиспользуемые компоненты
│   ├── layout/    # Sidebar, Topbar, Layout, PrivateRoute
│   └── ui/        # Toaster
├── lib/           # хелперы (utils, useWebSocket)
├── pages/         # экраны
├── store/         # zustand сторы (auth, notifications)
└── types/         # TypeScript типы
```

## Роли и страницы

| Страница | user | analyst | admin |
|---|---|---|---|
| Сканирования (свои) | ✅ | ✅ | ✅ |
| Загрузка документа | ✅ | ✅ | ✅ |
| Мой профиль | ✅ | ✅ | ✅ |
| Дашборд статистики | — | ✅ | ✅ |
| Управление правилами | — | — | ✅ |
| Пользователи | — | — | ✅ |
| Журнал аудита | — | — | ✅ |

## Особенности

- **Авто-refresh JWT** — interceptor в `api/client.ts` ловит 401 и обновляет токен
- **Polling** — список сканирований обновляется каждые 5 сек, детали — каждые 2 сек при processing
- **WebSocket** — real-time уведомления о завершении сканирований, авто-переподключение
- **Тосты** — нотификации в правом нижнем углу
- **Drag & Drop** — загрузка файлов
- **Локализация** — все строки на русском (метки, типы, статусы)
