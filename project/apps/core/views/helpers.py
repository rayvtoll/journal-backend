import base64
import io
from attr import dataclass
import matplotlib.pyplot as plt

COLOR_LIST = [
    "#47DBCD",
    "#F3A0F2",
    "#9D2EC5",
    "#661D98",
    "#F5B14C",
    "#2CBDFF",
    "#FF6F91",
    "#FF9671",
    "#FFC75F",
    "#008F7A",
    "#0081CF",
    "#F9F871",
    "#4CC9F0",
    "#4361EE",
    "#4895EF",
    "#4CC9F0",
    "#CE9FFC",
    "#00D4A6",
    "#FFD166",
    "#06AED5",
    "#EE4266",
    "#FF9F1C",
    "#2EC4B6",
    "#E71D36",
    "#FF6B6B",
    "#4D96FF",
    "#845EF7",
    "#FF77A9",
    "#9B5DE5",
    "#00B4D8",
    "#3A86FF",
    "#FB8B24",
    "#E76F51",
    "#2A9D8F",
    "#8AC926",
    "#F9C74F",
    "#A0E7E5",
    "#C77DFF",
    "#00CC66",
    "#FFB86B",
    "#66D9EF",
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


@dataclass
class WinStreak:
    """Dataclass for win/loss streak tracking."""

    longest_win_streak: int = 0
    longest_loss_streak: int = 0
    current_win_streak: int = 0
    current_loss_streak: int = 0

    def record_win(self):
        """Records a win and updates streaks."""
        self.current_win_streak += 1
        self.current_loss_streak = 0
        if self.current_win_streak > self.longest_win_streak:
            self.longest_win_streak = self.current_win_streak

    def record_loss(self):
        """Records a loss and updates streaks."""
        self.current_loss_streak += 1
        self.current_win_streak = 0
        if self.current_loss_streak > self.longest_loss_streak:
            self.longest_loss_streak = self.current_loss_streak
