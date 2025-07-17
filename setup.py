from setuptools import setup, find_packages

setup(
    name="airflow-dag-generator",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "airflow.plugins": [
            "dag_generator = airflow_dag_generator.plugin:DagGeneratorPlugin"
        ]
    },
)
