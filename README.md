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
├── requirements.txt       # Зависимости
└── .env.example           # Пример переменных окружения
```

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone <url>
cd hh_etl
```

### 2. Создать виртуальное окружение

```bash
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
# .venv\Scripts\activate       # Windows
```

### 3. Установить зависимости

> Airflow устанавливается отдельно, так как тянет много транзитивных зависимостей.
> Если Airflow не нужен, пропустите второй шаг.

```bash
# Основные зависимости
pip install requests beautifulsoup4 lxml tenacity polars pyarrow \
            pendulum sqlalchemy psycopg2-binary hydra-core tqdm papermill

# Airflow (опционально)
pip install apache-airflow
```

Либо всё сразу из файла (может потребоваться разрешение конфликтов):

```bash
pip install -r requirements.txt
```

### 4. Настроить переменные окружения

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

Загрузите переменные в текущую сессию:

```bash
export $(grep -v '^#' .env | xargs)
```

### 5. Подготовить PostgreSQL

Создайте базу данных и пользователя (если ещё не созданы):

```sql
CREATE DATABASE etl_db;
CREATE USER etl WITH PASSWORD 'ваш_пароль';
GRANT ALL PRIVILEGES ON DATABASE etl_db TO etl;
```

Схема `etl` и таблицы создаются автоматически при первом запуске ноутбука.

### 6. Настроить конфигурацию скрейпера

Откройте `conf/config.yaml` и при необходимости измените:

```yaml
hh_scraper:
  catalog_url: "https://hh.ru/vacancies/voditel"   # категория вакансий
  area: 1              # 1 = Москва, 0 = все регионы, 2 = Санкт-Петербург
  items_on_page: 100   # макс 100
  order_by: "publication_time"
  request_delay: 1.5   # задержка между страницами (сек)
```

### 7. Запустить ноутбук

```bash
jupyter notebook hh_etl.ipynb
# или
jupyter lab
```

Выполните все ячейки последовательно (Cell → Run All) либо по одной.

---

## Запуск через Airflow (опционально)

### Инициализация Airflow

```bash
export AIRFLOW_HOME=$(pwd)/airflow_home
airflow db init

airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname Admin \
  --role Admin \
  --email admin@example.com
```

### Подключить DAG

```bash
mkdir -p $AIRFLOW_HOME/dags
cp dags/hh_etl_dag.py $AIRFLOW_HOME/dags/
```

### Запустить планировщик и веб-сервер

```bash
# В двух отдельных терминалах:
airflow scheduler
airflow webserver --port 8080
```

Откройте [http://localhost:8080](http://localhost:8080) и включите DAG `hh_etl`.

---

## Проверка результатов

После запуска ноутбука можно проверить загруженные данные:

```sql
-- Сводка по таблице вакансий
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

| Переменная    | По умолчанию | Описание              |
|---------------|--------------|-----------------------|
| `DB_HOST`     | `localhost`  | Хост PostgreSQL       |
| `DB_PORT`     | `5432`       | Порт PostgreSQL       |
| `DB_NAME`     | `etl_db`     | Имя базы данных       |
| `DB_USER`     | `etl`        | Пользователь БД       |
| `DB_PASSWORD` | `password`   | Пароль пользователя   |

---

## Требования

- Python 3.11+
- PostgreSQL 14+
- Доступ в интернет (для скрейпинга hh.ru)
