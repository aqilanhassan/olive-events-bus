from setuptools import find_packages, setup

setup(
    name="olive_events_bus",
    version="1.0.1",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "aiokafka>=0.10.0",
        "pydantic>=2.0.0",
        "structlog>=23.0.0",
    ],
    description="Olive Events Bus SDK for Kafka event handling",
    author="Olive Team",
    package_data={
        "olive_events_bus": ["py.typed"],
    },
    include_package_data=True,
)
