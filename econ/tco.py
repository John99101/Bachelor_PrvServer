"""36-month TCO for RQ4, with the energy term removed (decision C2c).

No smart plug or RAPL data was collected, so this script computes only the
non-energy terms: hardware cost, admin time, and downtime cost. Energy is
reported in the thesis as "not executed — proposed protocol / future work".

Every input below must be either a measured value from this repo's data/ or a
clearly labelled assumption (see ASSUMPTIONS). The sensitivity sweep re-runs
the calculation with each cost parameter at +/-50% so the result is
defensible despite uncertain inputs.
"""
import json

MONTHS = 36

# ---- Assumptions (cite a source or mark "author's assumption") ----
ASSUMPTIONS = {
    "admin_eur_h": "author's assumption: informal hourly rate for admin time",
    "downtime_eur_h": "author's assumption: nominal cost of an hour of service downtime",
    "hw_eur": "author's assumption / quote for the hardware used in this study",
}


def tco(admin_min_yr, downtime_h_yr, admin_eur_h=4.50, downtime_eur_h=2.00, hw_eur=300):
    """Total cost of ownership over MONTHS, excluding energy."""
    years = MONTHS / 12
    admin = admin_min_yr / 60 * years * admin_eur_h
    downtime = downtime_h_yr * years * downtime_eur_h
    return round(hw_eur + admin + downtime, 2)


def sensitivity(admin_min_yr, downtime_h_yr, base_kwargs):
    """Re-run tco() with each cost parameter at +/-50%, others held at base."""
    results = {"base": tco(admin_min_yr, downtime_h_yr, **base_kwargs)}
    for param in ("admin_eur_h", "downtime_eur_h", "hw_eur"):
        for factor, label in ((0.5, "-50%"), (1.5, "+50%")):
            kwargs = dict(base_kwargs)
            kwargs[param] = base_kwargs[param] * factor
            results[f"{param}{label}"] = tco(admin_min_yr, downtime_h_yr, **kwargs)
    return results


if __name__ == "__main__":
    # Replace these with values measured in data/<variant>_maint.csv (RQ3)
    # and any observed downtime, per variant.
    admin_min_yr = 240
    downtime_h_yr = 6
    base_kwargs = {"admin_eur_h": 4.50, "downtime_eur_h": 2.00, "hw_eur": 300}

    base = tco(admin_min_yr, downtime_h_yr, **base_kwargs)
    sens = sensitivity(admin_min_yr, downtime_h_yr, base_kwargs)

    print(f"36-month TCO (excl. energy): EUR {base}")
    print("Sensitivity (+/-50% per parameter):")
    for k, v in sens.items():
        print(f"  {k}: EUR {v}")
    print("\nAssumptions:")
    for k, v in ASSUMPTIONS.items():
        print(f"  {k}: {v}")

    with open("data/tco.json", "w") as f:
        json.dump({"base": base, "sensitivity": sens, "assumptions": ASSUMPTIONS}, f, indent=2)
    print("\nsaved data/tco.json")
