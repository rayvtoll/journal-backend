import base64
import io
import matplotlib.pyplot as plt

COLOR_LIST = [
    "#47DBCD",
    "#F3A0F2",
    "#9D2EC5",
    "#661D98",
    "#F5B14C",
    "#2CBDFF",
]

INITIAL_CAPITAL = 10_000

SNS_THEME = dict(
    font="DejaVu Sans",
    rc={
        "axes.axisbelow": False,
        "axes.edgecolor": "lightgrey",
        "axes.facecolor": "None",
        "axes.grid": False,
        "axes.labelcolor": "white",
        "axes.spines.right": False,
        "axes.spines.top": False,
        "figure.facecolor": "black",
        "lines.solid_capstyle": "round",
        "patch.edgecolor": "white",
        "patch.force_edgecolor": True,
        "text.color": "white",
        "xtick.bottom": False,
        "xtick.color": "white",
        "xtick.direction": "out",
        "xtick.top": False,
        "ytick.color": "white",
        "ytick.direction": "out",
        "ytick.left": False,
        "ytick.right": False,
    },
)


def plotter(plt: plt, legend: bool = True) -> io.BytesIO:
    """functie die een plot als een plaatje teruggeeft"""

    plt.grid(visible=True, which="major", axis="y", color="#444444", linestyle="--")
    if legend:
        plt.legend(frameon=False)
    s = io.BytesIO()
    plt.savefig(s, format="png", bbox_inches="tight")
    plt.close()
    return s


def image_encoder(s: io.BytesIO) -> str:
    """functie die plaatje als base64 verpakt zodat deze niet op de server hoeft te worden opgeslagen"""

    return base64.b64encode(s.getvalue()).decode("utf-8").replace("\n", "")
