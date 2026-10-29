/*
    Fractalchemy formula library — translated from the JWildfire variation
        ComplexFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double complex_cospow;
    double complex_cosx1;
    double complex_cosx2;
    double complex_cosy1;
    double complex_cosy2;
    double complex_coshpow;
    double complex_coshx1;
    double complex_coshx2;
    double complex_coshy1;
    double complex_coshy2;
    double complex_cotpow;
    double complex_cotx1;
    double complex_cotx2;
    double complex_coty1;
    double complex_coty2;
    double complex_cothpow;
    double complex_cothx1;
    double complex_cothx2;
    double complex_cothy1;
    double complex_cothy2;
    double complex_cscpow;
    double complex_cscx1;
    double complex_cscx2;
    double complex_cscy1;
    double complex_cscy2;
    double complex_cschpow;
    double complex_cschx1;
    double complex_cschx2;
    double complex_cschy1;
    double complex_cschy2;
    double complex_exppow;
    double complex_expx1;
    double complex_expy1;
    double complex_expy2;
    double complex_secpow;
    double complex_secx1;
    double complex_secx2;
    double complex_secy1;
    double complex_secy2;
    double complex_sechpow;
    double complex_sechx1;
    double complex_sechx2;
    double complex_sechy1;
    double complex_sechy2;
    double complex_sinpow;
    double complex_sinx1;
    double complex_sinx2;
    double complex_siny1;
    double complex_siny2;
    double complex_sinhpow;
    double complex_sinhx1;
    double complex_sinhx2;
    double complex_sinhy1;
    double complex_sinhy2;
    double complex_tanpow;
    double complex_tanx1;
    double complex_tanx2;
    double complex_tany1;
    double complex_tany2;
    double complex_tanhpow;
    double complex_tanhx1;
    double complex_tanhx2;
    double complex_tanhy1;
    double complex_tanhy2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("complex");

APO_VARIABLES(
    VAR_REAL(complex_cospow, 1),
    VAR_REAL(complex_cosx1, 1),
    VAR_REAL(complex_cosx2, 1),
    VAR_REAL(complex_cosy1, 1),
    VAR_REAL(complex_cosy2, 1),
    VAR_REAL(complex_coshpow, 0),
    VAR_REAL(complex_coshx1, 1),
    VAR_REAL(complex_coshx2, 1),
    VAR_REAL(complex_coshy1, 1),
    VAR_REAL(complex_coshy2, 1),
    VAR_REAL(complex_cotpow, 0),
    VAR_REAL(complex_cotx1, 2),
    VAR_REAL(complex_cotx2, 2),
    VAR_REAL(complex_coty1, 2),
    VAR_REAL(complex_coty2, 2),
    VAR_REAL(complex_cothpow, 0),
    VAR_REAL(complex_cothx1, 2),
    VAR_REAL(complex_cothx2, 2),
    VAR_REAL(complex_cothy1, 2),
    VAR_REAL(complex_cothy2, 2),
    VAR_REAL(complex_cscpow, 0),
    VAR_REAL(complex_cscx1, 1),
    VAR_REAL(complex_cscx2, 1),
    VAR_REAL(complex_cscy1, 1),
    VAR_REAL(complex_cscy2, 1),
    VAR_REAL(complex_cschpow, 0),
    VAR_REAL(complex_cschx1, 1),
    VAR_REAL(complex_cschx2, 1),
    VAR_REAL(complex_cschy1, 1),
    VAR_REAL(complex_cschy2, 1),
    VAR_REAL(complex_exppow, 0),
    VAR_REAL(complex_expx1, 1),
    VAR_REAL(complex_expy1, 1),
    VAR_REAL(complex_expy2, 1),
    VAR_REAL(complex_secpow, 0),
    VAR_REAL(complex_secx1, 1),
    VAR_REAL(complex_secx2, 1),
    VAR_REAL(complex_secy1, 1),
    VAR_REAL(complex_secy2, 1),
    VAR_REAL(complex_sechpow, 0),
    VAR_REAL(complex_sechx1, 1),
    VAR_REAL(complex_sechx2, 1),
    VAR_REAL(complex_sechy1, 1),
    VAR_REAL(complex_sechy2, 1),
    VAR_REAL(complex_sinpow, 0),
    VAR_REAL(complex_sinx1, 1),
    VAR_REAL(complex_sinx2, 1),
    VAR_REAL(complex_siny1, 1),
    VAR_REAL(complex_siny2, 1),
    VAR_REAL(complex_sinhpow, 0),
    VAR_REAL(complex_sinhx1, 1),
    VAR_REAL(complex_sinhx2, 1),
    VAR_REAL(complex_sinhy1, 1),
    VAR_REAL(complex_sinhy2, 1),
    VAR_REAL(complex_tanpow, 0),
    VAR_REAL(complex_tanx1, 2),
    VAR_REAL(complex_tanx2, 2),
    VAR_REAL(complex_tany1, 2),
    VAR_REAL(complex_tany2, 2),
    VAR_REAL(complex_tanhpow, 0),
    VAR_REAL(complex_tanhx1, 2),
    VAR_REAL(complex_tanhx2, 2),
    VAR_REAL(complex_tanhy1, 2),
    VAR_REAL(complex_tanhy2, 2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = 0.0, y = 0.0;
    if(VAR(complex_cospow) != 0) {
        double cossin = sin(FTx * VAR(complex_cosx1));
        double coscos = cos(FTx * VAR(complex_cosx2));
        double cossinh = sinh(FTy * VAR(complex_cosy1));
        double coscosh = cosh(FTy * VAR(complex_cosy2));
        x += VAR(complex_cospow) * coscos * coscosh;
        y -= VAR(complex_cospow) * cossin * cossinh;
    }
    if(VAR(complex_coshpow) != 0) {
        double coshsin = sin(FTy * VAR(complex_coshy1));
        double coshcos = cos(FTy * VAR(complex_coshy2));
        double coshsinh = sinh(FTx * VAR(complex_coshx1));
        double coshcosh = cosh(FTx * VAR(complex_coshx2));
        x += VAR(complex_coshpow) * coshcosh * coshcos;
        y += VAR(complex_coshpow) * coshsinh * coshsin;
    }
    if(VAR(complex_cotpow) != 0) {
        double cotsin = sin(VAR(complex_cotx1) * FTx);
        double cotcos = cos(VAR(complex_cotx2) * FTx);
        double cotsinh = sinh(VAR(complex_coty1) * FTy);
        double cotcosh = cosh(VAR(complex_coty2) * FTy);
        double cotden = 1.0 / (cotcosh - cotcos);
        x += VAR(complex_cotpow) * cotden * cotsin;
        y -= VAR(complex_cotpow) * cotden * cotsinh;
    }
    if(VAR(complex_cothpow) != 0) {
        double cothsin = sin(VAR(complex_cothy1) * FTy);
        double cothcos = cos(VAR(complex_cothy2) * FTy);
        double cothsinh = sinh(VAR(complex_cothx1) * FTx);
        double cothcosh = cosh(VAR(complex_cothx2) * FTx);
        double cothd = (cothcosh - cothcos);
        if(cothd == 0) return;
        double cothden = 1.0 / cothd;
        x += VAR(complex_cothpow) * cothden * cothsinh;
        y += VAR(complex_cothpow) * cothden * cothsin;
    }
    if(VAR(complex_cscpow) != 0) {
        double cscsin = sin(FTx * VAR(complex_cscx1));
        double csccos = cos(FTx * VAR(complex_cscx2));
        double cscsinh = sinh(FTy * VAR(complex_cscy1));
        double csccosh = cosh(FTy * VAR(complex_cscy2));
        double cscd = (cosh(2.0 * FTy) - cos(2.0 * FTx));
        if(cscd == 0) {
            return;
        }
        double cscden = 2.0 / cscd;
        x += VAR(complex_cscpow) * cscden * cscsin * csccosh;
        y -= VAR(complex_cscpow) * cscden * csccos * cscsinh;
    }
    if(VAR(complex_cschpow) != 0) {
        double cschsin = sin(FTy * VAR(complex_cschy1));
        double cschcos = cos(FTy * VAR(complex_cschy2));
        double cschsinh = sinh(FTx * VAR(complex_cschx1));
        double cschcosh = cosh(FTx * VAR(complex_cschx2));
        double cschd = (cosh(2.0 * FTx) - cos(2.0 * FTy));
        if(cschd == 0) {
            return;
        }
        double cschden = 2.0 / cschd;
        x += VAR(complex_cschpow) * cschden * cschsinh * cschcos;
        y -= VAR(complex_cschpow) * cschden * cschcosh * cschsin;
    }
    if(VAR(complex_exppow) != 0) {
        double expe = exp(FTx * VAR(complex_expx1));
        double expsin = sin(FTy * VAR(complex_expy1));
        double expcos = cos(FTy * VAR(complex_expy2));
        x += VAR(complex_exppow) * expe * expcos;
        y += VAR(complex_exppow) * expe * expsin;
    }
    if(VAR(complex_secpow) != 0) {
        double secsin = sin(FTx * VAR(complex_secx1));
        double seccos = cos(FTx * VAR(complex_secx2));
        double secsinh = sinh(FTy * VAR(complex_secy1));
        double seccosh = cosh(FTy * VAR(complex_secy2));
        double secd = (cos(2.0 * FTx) + cosh(2.0 * FTy));
        if(secd == 0) {
            return;
        }
        double secden = 2.0 / secd;
        x += VAR(complex_secpow) * secden * seccos * seccosh;
        y += VAR(complex_secpow) * secden * secsin * secsinh;
    }
    if(VAR(complex_sechpow) != 0) {
        double sechsinh = sin(FTy * VAR(complex_sechy1));
        double sechcosh = cos(FTy * VAR(complex_sechy2));
        double sechsin = sinh(FTx * VAR(complex_sechx1));
        double sechcos = cosh(FTx * VAR(complex_sechx2));
        double sechd = (cos(2.0 * FTy) + cosh(2.0 * FTx));
        if(sechd == 0) {
            return;
        }
        double sechden = 2.0 / sechd;
        x += VAR(complex_sechpow) * sechden * sechcos * sechcosh;
        y -= VAR(complex_sechpow) * sechden * sechsin * sechsinh;
    }
    if(VAR(complex_tanpow) != 0) {
        double tansin = sin(VAR(complex_tanx1) * FTx);
        double tancos = cos(VAR(complex_tanx2) * FTx);
        double tansinh = sinh(VAR(complex_tany1) * FTy);
        double tancosh = cosh(VAR(complex_tany2) * FTy);
        double tand = (tancos + tancosh);
        if(tand == 0) {
            return;
        }
        double tanden = 1.0 / tand;
        x += VAR(complex_tanpow) * tanden * tansin;
        y += VAR(complex_tanpow) * tanden * tansinh;
    }
    if(VAR(complex_tanhpow) != 0) {
        double tanhsin = sin(FTy * VAR(complex_tanhy1));
        double tanhcos = cos(FTy * VAR(complex_tanhy2));
        double tanhsinh = sinh(FTx * VAR(complex_tanhx1));
        double tanhcosh = cosh(FTx * VAR(complex_tanhx2));
        double tanhd = (tanhcos + tanhcosh);
        if(tanhd == 0) {
            return;
        }
        double tanhden = 1.0 / tanhd;
        x += VAR(complex_tanhpow) * tanhden * tanhsinh;
        y += VAR(complex_tanhpow) * tanhden * tanhsin;
    }
    if(VAR(complex_sinpow) != 0) {
        double sinsin = sin(FTx * VAR(complex_sinx1));
        double sincos = cos(FTx * VAR(complex_sinx2));
        double sinsinh = sinh(FTy * VAR(complex_siny1));
        double sincosh = cosh(FTy * VAR(complex_siny2));
        x += VAR(complex_sinpow) * sinsin * sincosh;
        y += VAR(complex_sinpow) * sincos * sinsinh;
    }
    if(VAR(complex_sinhpow) != 0) {
        double sinhsin = sin(FTy * VAR(complex_sinhy1));
        double sinhcos = cos(FTy * VAR(complex_sinhy2));
        double sinhsinh = sinh(FTx * VAR(complex_sinhx1));
        double sinhcosh = cosh(FTx * VAR(complex_sinhx2));
        x += VAR(complex_sinhpow) * sinhsinh * sinhcos;
        y += VAR(complex_sinhpow) * sinhcosh * sinhsin;
    }
    FPx += VVAR * x;
    FPy += VVAR * y;
    
    return TRUE;
}
