# HH.ru ELT Pipeline

Инкрементальный сбор вакансий с [hh.ru](https://hh.ru/vacancies/voditel) через веб-скрейпинг,
загрузка в PostgreSQL и сохранение в Parquet-файлы (data lake).

## Структура проекта

```
hh_etl/
├── conf/
│   └── config.yaml        # Конфигурация (Hydra)
├── dags/
│   └── hh_etl_dag.py      # Airflow DAG
├── data_lake/             # Parquet-файлы (создаётся автоматически)
├── logs/                  # Лог-файлы (создаётся автоматически)
├── hh_etl.ipynb           # Основной ETL-ноутбук
├── requirements.txt       # Зависимости (без Airflow)
├── .env.example           # Пример переменных окружения
└── README.md
```

---

## Требования

- Python 3.11+
- PostgreSQL 14+
- Доступ в интернет (для скрейпинга hh.ru)

---

## Шаг 1 — Подготовка (для обоих вариантов)

### 1.1 Клонировать репозиторий

```bash
git clone <url>
cd hh_etl
```

### 1.2 Настроить переменные окружения

```bash
cp .env.example .env
```

Откройте `.env` и укажите параметры вашей PostgreSQL:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=etl_db
DB_USER=etl
DB_PASSWORD=ваш_пароль
```

### 1.3 Подготовить PostgreSQL

```sql
CREATE DATABASE etl_db;
CREATE USER etl WITH PASSWORD 'ваш_пароль';
GRANT ALL PRIVILEGES ON DATABASE etl_db TO etl;

\c etl_db
GRANT ALL ON SCHEMA public TO etl;
```

Схема `etl` и таблицы создаются автоматически при первом запуске.

### 1.4 Настроить конфигурацию скрейпера

Откройте `conf/config.yaml` и при необходимости измените:

```yaml
hh_scraper:
  catalog_url: "https://hh.ru/vacancies/voditel"   # категория вакансий
  area: 1              # 1 = Москва, 0 = все регионы, 2 = Санкт-Петербург
  items_on_page: 100
  order_by: "publication_time"
  request_delay: 1.5
```

---

## Вариант A — Запуск вручную (без Airflow)

### A.1 Создать виртуальное окружение

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows
```

### A.2 Установить зависимости

```bash
# Fedora / RHEL — системные библиотеки для lxml
sudo dnf install -y libxml2-devel libxslt-devel

pip install -r requirements.txt
```

### A.3 Загрузить переменные окружения

```bash
export $(grep -v '^#' .env | xargs)
```

### A.4 Запустить ноутбук

```bash
jupyter notebook hh_etl.ipynb
```

Откройте браузер по адресу из терминала и выполните **Cell → Run All**.

---

## Вариант B — Запуск по расписанию через Airflow

> Airflow устанавливается в **отдельный** venv, так как конфликтует с зависимостями ноутбука.

### B.1 Создать venv для Airflow

```bash
python -m venv .venv-airflow
source .venv-airflow/bin/activate
```

### B.2 Установить Airflow

```bash
pip install apache-airflow papermill pendulum
```

### B.3 Инициализировать Airflow

```bash
export AIRFLOW_HOME=$(pwd)/airflow_home

airflow db migrate

airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname Admin \
  --role Admin \
  --email admin@example.com
```

### B.4 Подключить DAG

```bash
mkdir -p $AIRFLOW_HOME/dags
cp dags/hh_etl_dag.py $AIRFLOW_HOME/dags/
```

### B.5 Загрузить переменные окружения

```bash
export $(grep -v '^#' .env | xargs)
```

### B.6 Запустить Airflow

```bash
airflow standalone
```

Дождитесь строки:

```
standalone | Airflow is ready
standalone | Login with username: admin  password: ...
standalone | Airflow Webserver is now available at: http://0.0.0.0:8080
```

Откройте [http://localhost:8080](http://localhost:8080), найдите DAG `hh_etl` и нажмите **▶ Trigger DAG**.

> **Расписание по умолчанию** — каждый день в 06:00 UTC.  
> Изменить можно в `dags/hh_etl_dag.py`, параметр `schedule=`.

---

## Проверка результатов

```bash
psql -U etl -d etl_db -h localhost
```

```sql
-- Сводка по вакансиям
SELECT
    COUNT(*)                               AS total,
    COUNT(*) FILTER (WHERE NOT is_deleted) AS active,
    MAX(extracted_dttm)                    AS last_run
FROM etl.hh_vacancies;

-- История ETL-запусков
SELECT etl_id, started_at, status,
       vacancies_found, vacancies_inserted, vacancies_updated
FROM etl.hh_etl_runs
ORDER BY started_at DESC
LIMIT 10;
```

Parquet-файлы сохраняются в:

```
data_lake/hh_vacancies/year=YYYY/month=MM/day=DD/<etl_id>.parquet
```

---

## Переменные окружения

| Переменная    | По умолчанию | Описание            |
|---------------|--------------|---------------------|
| `DB_HOST`     | `localhost`  | Хост PostgreSQL     |
| `DB_PORT`     | `5432`       | Порт PostgreSQL     |
| `DB_NAME`     | `etl_db`     | Имя базы данных     |
| `DB_USER`     | `etl`        | Пользователь БД     |
| `DB_PASSWORD` | `password`   | Пароль пользователя |
