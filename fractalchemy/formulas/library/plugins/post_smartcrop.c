/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/post_smartcrop.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct {
    double post_scrop_radius, post_scrop_scatter, post_scrop_power, post_scrop_offset, post_scrop_edge, post_scrop_distortion, post_scrop_roundstr, post_scrop_roundwidth;
    double post_scrop_workpower, post_scrop_workradius, post_scrop_alpha, post_scrop_roundcoeff;
    double post_scrop_x, post_scrop_y, post_scrop_z, post_scrop_c;
    int post_scrop_mode, post_scrop_cropmode, post_scrop_static;
    int post_scrop_edgeon, post_scrop_distortionon, post_scrop_limiton, post_scrop_roundingon, post_scrop_rpoweron, post_scrop_radial;
} Variables;

// (missing include apoplugin_with_dc.h)

APO_PLUGIN("post_smartcrop");
APO_VARIABLES(
        VAR_REAL(post_scrop_power, 4.0),
        VAR_REAL(post_scrop_radius, 1.0),
        VAR_REAL(post_scrop_roundstr, 0.0),
        VAR_REAL(post_scrop_roundwidth, 1.0),
        VAR_REAL(post_scrop_distortion, 1.0),
        VAR_REAL(post_scrop_edge, 0.0),
        VAR_REAL(post_scrop_scatter, 0.0),
        VAR_REAL(post_scrop_offset, 0.0),
        VAR_INTEGER_RANGE(post_scrop_cropmode, 0, 2, 1),
        VAR_INTEGER_RANGE(post_scrop_static, -1, 2, 1)
        );

int PluginVarPrepare(Variation* vp) {
    VAR(post_scrop_mode) = (VAR(post_scrop_power) > 0) == (VAR(post_scrop_radius) > 0);
    VAR(post_scrop_workradius) = fabs(VAR(post_scrop_radius));
    VAR(post_scrop_workpower) = fabs(VAR(post_scrop_power));
    if (VAR(post_scrop_workpower) < 2) {
        VAR(post_scrop_workpower) = VAR(post_scrop_workpower) * M_PI;
        VAR(post_scrop_radial) = 1;
    } else {
        VAR(post_scrop_radial) = 0;
        VAR(post_scrop_alpha) = M_2PI / VAR(post_scrop_workpower);
        VAR(post_scrop_roundcoeff) = VAR(post_scrop_roundstr) / sin(VAR(post_scrop_alpha) / 2) / VAR(post_scrop_workpower) * 2;
    }
    VAR(post_scrop_x) = VAR(post_scrop_y) = VAR(post_scrop_z) = VAR(post_scrop_c) = 0;
    return TRUE;
}

int PluginVarCalc(Variation* vp) {
    double ang, rad;
    double xi = VAR(post_scrop_static) == 2 ? FPx : FTx, yi = VAR(post_scrop_static) == 2 ? FPy : FTy, zi = VAR(post_scrop_static) == 2 ? FPz : FTz;

    ang = atan2(yi, xi);
    rad = sqrt(xi * xi + yi * yi);

    if (VAR(post_scrop_radial)) {
        double edge = VAR(post_scrop_edge) * (random01() - 0.5);
        double xang = ang / M_2PI + 1 + edge;
        xang = (xang - (int) xang) * M_2PI;
        if ((xang > VAR(post_scrop_workpower)) == VAR(post_scrop_mode)) {
            if (VAR(post_scrop_cropmode) == 2) {
                if ((VAR(post_scrop_static) == 2) || (VAR(post_scrop_static) == -1)) {
                    FPx = VAR(post_scrop_x);
                    FPy = VAR(post_scrop_y);
                    FPz = VAR(post_scrop_z);
                    TC = VAR(post_scrop_c);
                    return 1;
                }
                FPx += VAR(post_scrop_x);
                FPy += VAR(post_scrop_y);
                FPz += VAR(post_scrop_z);
                TC = VAR(post_scrop_c);
                return 1;
            }
            double s, c;
            fsincos(((int) (random01() * 2)) ? VAR(post_scrop_workpower) + (random01() * VAR(post_scrop_scatter) + VAR(post_scrop_offset) + edge) * M_PI : -(random01() * VAR(post_scrop_scatter) + VAR(post_scrop_offset) + edge) * M_PI, &s, &c);
            if ((VAR(post_scrop_static) == 2) || (VAR(post_scrop_static) == -1)) {
                FPx = VVAR * rad * c;
                FPy = VVAR * rad * s;
                FPz = VVAR * zi;
                return 1;
            }
            FPx += VVAR * rad * c;
            FPy += VVAR * rad * s;
            FPz += VVAR * zi;
            return 1;
        }
    } else {
        double coeff;
        if (VAR(post_scrop_distortion) == 0.0)
            coeff = 1;
        else {
            double xang = (ang + M_PI) / VAR(post_scrop_alpha);
            xang = xang - (int) xang;
            xang = (xang < 0.5) ? xang : 1 - xang;
            coeff = 1 / cos(xang * VAR(post_scrop_alpha));
            if (VAR(post_scrop_roundstr) != 0.0) {
                const double wwidth = ((VAR(post_scrop_roundwidth) != 1.0) ? exp(log(xang * 2) * VAR(post_scrop_roundwidth)) : (xang * 2)) * VAR(post_scrop_roundcoeff);
                coeff = fabs((1 - wwidth) * coeff + wwidth);
            }
            if (VAR(post_scrop_distortion) != 1.0)
                coeff = exp(log(coeff) * VAR(post_scrop_distortion));
        }
        const double xr = coeff * ((VAR(post_scrop_edge) != 0.0) ? VAR(post_scrop_workradius) + VAR(post_scrop_edge) * (random01() - 0.5) : VAR(post_scrop_workradius));

        if ((rad > xr) == VAR(post_scrop_mode)) {
            if (VAR(post_scrop_cropmode) == 2) {
                if ((VAR(post_scrop_static) == 2) || (VAR(post_scrop_static) == -1)) {
                    FPx = VAR(post_scrop_x);
                    FPy = VAR(post_scrop_y);
                    FPz = VAR(post_scrop_z);
                    TC = VAR(post_scrop_c);
                    return 1;
                }
                FPx += VAR(post_scrop_x);
                FPy += VAR(post_scrop_y);
                FPz += VAR(post_scrop_z);
                TC = VAR(post_scrop_c);
                return 1;
            }
            const double rdc = (VAR(post_scrop_cropmode) > 0) * xr + coeff * (random01() * VAR(post_scrop_scatter) + VAR(post_scrop_offset));
            double s, c;
            fsincos(ang, &s, &c);
            if ((VAR(post_scrop_static) == 2) || (VAR(post_scrop_static) == -1)) {
                FPx = VVAR * rdc * c;
                FPy = VVAR * rdc * s;
                FPz = VVAR * zi;
                return 1;
            }
            FPx += VVAR * rdc * c;
            FPy += VVAR * rdc * s;
            FPz += VVAR * zi;
            return 1;
        }
    }

    VAR(post_scrop_x) = VVAR * xi;
    VAR(post_scrop_y) = VVAR * yi;
    VAR(post_scrop_z) = VVAR * zi;
    if (VAR(post_scrop_cropmode) == 2)
        VAR(post_scrop_c) = TC;

    if (VAR(post_scrop_static) > 0) {
        FPx = VAR(post_scrop_x);
        FPy = VAR(post_scrop_y);
        FPz = VAR(post_scrop_z);
        return 1;
    }

    FPx += VAR(post_scrop_x);
    FPy += VAR(post_scrop_y);
    FPz += VAR(post_scrop_z);
    return 1;
}