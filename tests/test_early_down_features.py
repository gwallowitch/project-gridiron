import polars as pl
import pytest

from gridiron.features.early_down import build_early_down_features


def test_current_week_cannot_leak():
    schedule=pl.DataFrame({"game_id":["g1","g2"],"season":[2024,2024],"week":[1,2],"home_team":["AAA","AAA"],"away_team":["BBB","BBB"]})
    pbp=pl.DataFrame({"game_id":["g1","g1","g2","g2"],"season":[2024]*4,"week":[1,1,2,2],"posteam":["AAA","BBB","AAA","BBB"],"defteam":["BBB","AAA","BBB","AAA"],"down":[1,2,1,2],"play_type":["pass","run","pass","run"],"epa":[1.0,-0.5,99.0,-99.0],"success":[1.0,0.0,1.0,0.0],"yards_gained":[25.0,2.0,80.0,-5.0]})
    out=build_early_down_features(schedule,pbp)
    w1=out.filter(pl.col("week")==1).row(0,named=True); w2=out.filter(pl.col("week")==2).row(0,named=True)
    assert w1["home_early_down_known"] is False
    assert w2["home_off_early_down_epa"] == pytest.approx(1.0)
    assert w2["away_off_early_down_epa"] == pytest.approx(-0.5)
