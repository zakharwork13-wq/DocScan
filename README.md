# DocScan

Веб-приложение для поиска персональных данных в документах.

Загружаете документ (DOCX, PDF, XLSX, TXT, RTF, изображение) — система ищет в нём паспортные данные, СНИЛС, ИНН, номера банковских карт, телефоны, email и другие ПДн граждан РФ. На выходе — список найденных данных и категория конфиденциальности документа.

## Что нужно установить

- **Python 3.11+** — https://www.python.org/
- **Node.js 20+** — https://nodejs.org/
- **PostgreSQL 15+** — https://www.postgresql.org/download/

## Запуск

### 1. Подготовить базу данных

После установки PostgreSQL откройте psql и выполните:

```sql
CREATE USER docscan WITH PASSWORD 'docscan123';
CREATE DATABASE docscan OWNER docscan;
```

### 2. Запустить backend

```powershell
cd backend

# Установить зависимости
pip install -r requirements.txt

# Создать файл .env (взять за основу .env.example в корне)
# Поменять POSTGRES_PASSWORD на пароль вашего PostgreSQL

# Инициализировать БД (миграции + создать админа)
python -m scripts.init

# Запустить API
python -m uvicorn app.main:app --reload --port 8000
```

API будет доступен на **http://localhost:8000**

### 3. Запустить frontend

В новом окне терминала:

```powershell
cd frontend
npm install
npm run dev
```

Откройте в браузере: **http://localhost:5173/**

### 4. Войти

```
Логин:  admin
Пароль: AdminPass123!
```




