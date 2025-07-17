FROM apache/airflow:2.10.2-python3.10

USER root

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Копируем файлы установки
COPY ../setup.py .
COPY ../pyproject.toml .
COPY ../README.md .

# Копируем исходный код
COPY ../airflow_dag_generator ./airflow_dag_generator

# Устанавливаем библиотеку
RUN pip3 install .

USER airflow
