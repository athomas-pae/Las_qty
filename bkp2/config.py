import welly.quality as qty

def get_tests():
    """Return a dictionary of tests to be applied to curves."""
    tests = {
        "All": [qty.no_similarities],
        "Each": [qty.no_monotonic, qty.no_flat],
        "GR": [qty.all_positive, qty.all_between(10, 100)],
        "DEN": [qty.all_between(0, 60)],
        "DEN_PE": [qty.all_between(0, 3)],
        "SONIC_DT": [qty.all_between(60, 140)],
        "SONIC_POR": [qty.all_between(0, 3)],
        "NEU": [qty.all_between(0.1, 0.5)],
        "IND": [qty.all_between(0, 100)],
        "CALI": [qty.all_between(5, 25)],
        "SP": [qty.all_between(-80, 0)],
        "RAT": [qty.all_between(0, 5)],
        "DEPTH": [qty.all_between(0, 5000)],
        "COND": [qty.all_between(0, 2000)],
        "RES": [qty.all_between(0, 100)],
        "CBL": [qty.all_between(0, 100)],
        "PSEU_RT": [qty.all_between(0, 100)],
        "PSEU_SP": [qty.all_between(0, 100)],
        "MIN_PNX": [qty.all_between(0, 100)],
        "MIN_NEXT": [qty.all_between(0, 100)],
        "PSEU_CO": [qty.all_between(0, 100)],
        "CORR_MIT": [qty.all_between(0, 20)],
        "CORR_MTT": [qty.all_between(0, 100)]
    }

    return tests

def get_alias():
    """Return a dictionary of aliases for curve names."""
    alias = {
        "GR": ["GR_NORM", "GRC", "GR"],
        "DEN": ["RHOB_NORM", "ZDENC", "ZDEN", "RHOB", "RHOZ", "DPHI", "PORZC"],
        "DEN_PE": ["PE"],
        "NEU": ["NPHI_NORM", "CNC", "CNCF", "CN", "NPHI", "NAPI"],
        "SONIC_DT": ["DT_NORM", "DTC", "DT"],
        "SONIC_POR": ["SPHI", "PORA"],
        "IND": ["RT90", "M2R9"],
        "CALI": ["CALI", "CAL"],
        "SP": ["SPB", "SPO"],
        "RAT": ["RAT9020"],
        "DEPTH": ["DEPT"],
        "COND": ["CT90", "M2CX"],
        "RES": ["T2PT", "MPHS", "T2PI", "MPHE", "T2P_MICRO", "MBVI"],
        "CBL": ["CBL", "CBLF", "AMP3FT", "DCBL", "AMP", "AM3F"],
        "PSEU_RT": ["PSEUDORES", "RDPDK", "Pseudo_RT", "RT90_HAT", "PseudoResistivity", "PSEUDORESISTIVI"],
        "PSEU_SP": ["PSEUDOSP", "SigmaPseudoSP", "SPPDK", "Pseudo_SP", "SIGMAPSEUDOSP"],
        "MIN_PNX": ["RHGE_INCP"],
        "MIN_NEXT": ["SIGE_INCP"],
        "PSEU_CO": ["C01","C02","C03"],
        "CORR_MIT": ["FING01","FING12","FING24"],
        "CORR_MTT": ["MTH01","MTH06","MTH12"]
    }
    return alias

def get_service_groups():
    """Return a dictionary of service groups and their required curves."""
    service_groups = {
        "COMBO BASICO": ["CALI", "GR", "IND", "SP"],
        "SONICO": ["SONIC_POR"],
        "DENSIDAD": ["DEN"],
        "NEUTRON": ["NEU"],
        "RESONANCIA MAGNETICA": ["RES"],
        "PERFIL DE CEMENTO": ["CBL"],
        "PSEUDO PERFILES (PseudoRT - PseudoSP)": ["PSEU_RT"],
        "MINERALOGICO": ["MIN_PNX","MIN_NEXT"],
        "PSEUDO CARBONO OXIGENO": ["PSEU_CO"],
        "CORROSION": ["CORR_MIT", "CORR_MTT"]
    }
    return service_groups

def has_si_units(curve):
    """Check if the curve has SI units."""
    return curve.units.lower() in ['gapi', 'g/cc', 'pu', 'us/f', 'ohmm', 'in', 'mv', 'lb/deg']

def get_service_units():
    """Return a dictionary of expected units for each service."""
    service_units = {
        "GR": "gapi",
        "DEN": "g/cc",
        "DEN_PE": "b/e",
        "SONIC_DT": "uspf",
        "SONIC_POR": "g/cc",
        "NEU": "g/cc",
        "IND": "ohmm",
        "CALI": "in",
        "SP": "mV",
        "RAT": "lb/deg",
        "DEPTH": "m",
        "COND": "mmho",
        "RES": "decp",
        "CBL": "mV",
        "PSEU_RT": "ohmm",
        "PSEU_SP": "mV",
        "MIN_PNX": "g/cm3",
        "MIN_NEXT": "cu",
        "PSEU_CO": "ppm",
        "CORR_MIT": "mm",
        "CORR_MTT": "rad",
    }

    return service_units

def apply_tests(curve, test_funcs):
    """Apply a list of test functions to a curve and return the results."""
    results = {}
    for test in test_funcs:
        try:
            results[test.__name__] = test(curve)
        except Exception as e:
            results[test.__name__] = str(e)
    return results

def highlight_alias(val):
    """Highlight alias cells."""
    color = 'green' if val != 'N/A' else ''
    return f'background-color: {color}'

def highlight_empty(val):
    """Highlight empty cells."""
    color = 'red' if val == 'Yes' else ''
    return f'background-color: {color}'

def validate_header(well_info_df):
    """Validate the header of the well information DataFrame."""
    mnem_to_description = {
        "SRVC": "SERVICE COMPANY",
        "EKB": "ELEVACION DE KB",
        "EGL": "NIVEL TERRENO",
        "APD": "ALTURA MESA",
        "FL1": "COORDENADA X",
        "FL2": "COORDENADA Y",
        "FL3": "COORDENADA Z",
        "RIG": "NOMBRE EQUIPO",
        "FLD": "NOMBRE CAMPO",
        "WELL": "NOMBRE POZO",
        "COMP": "OPERADORA",
        "DATE": "FECHA"
    }

    header_requirements = list(mnem_to_description.keys())
    header_compliance = all(item in well_info_df['MNEM'].values for item in header_requirements)
    non_compliant_variables = [item for item in header_requirements if item not in well_info_df['MNEM'].values]
    missing_descriptions = [
        f"{mnem_to_description[item]} ({item})"
        if item in mnem_to_description else f"Description not found ({item})"
        for item in non_compliant_variables
    ]
    return header_compliance, missing_descriptions
