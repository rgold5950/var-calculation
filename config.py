from src.port import BondIndex, Port
import datetime

END_DATE = datetime.date.today()
START_DATE = END_DATE - datetime.timedelta(days=365 * 2)

# Create a dictionary of BondIndex instances
PORT: Port = [
    BondIndex(
        name="AAA",
        yield_index="BAMLC0A1CAAAEY",
        price_index="BAMLCC0A1AAATRIV",
        weight=0.25,
    ),
    BondIndex(
        name="BBB",
        yield_index="BAMLC0A4CBBBEY",
        price_index="BAMLCC0A4BBBTRIV",
        weight=0.25,
    ),
    BondIndex(
        name="BB",
        yield_index="BAMLH0A1HYBBEY",
        price_index="BAMLHYH0A1BBTRIV",
        weight=0.25,
    ),
    BondIndex(
        name="CCC",
        yield_index="BAMLH0A3HYCEY",
        price_index="BAMLHYH0A3CMTRIV",
        weight=0.25,
    ),
]
