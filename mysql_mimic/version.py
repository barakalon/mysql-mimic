"""mysql-mimic version information"""

__version__ = "2.2.7"


def main(name: str) -> None:
    if name == "__main__":
        print(__version__)


main(__name__)
