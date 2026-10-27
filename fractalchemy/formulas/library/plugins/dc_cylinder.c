/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/DC-Cylinder.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

    /*
        DC-Cylinder Apophysis Plugin
        This is a combo plugin based on the Rod Plugin by Branden Brown, a.k.a. zephyrtronium
        and the DC_linear Plugin by Georg Kiehne a.k.a. Xyruso2
        This plugin is free software; you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation; either version 3 of the License, or
        (at your option) any later version.
        This plugin is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.
     
        You should have received a copy of the GNU General Public License
        along with this plugin; if not, see <http://www.gnu.org/licenses/>.
    */
     
    typedef struct
    {
        double dc_cyl_offset, dc_cyl_angle, dc_cyl_scale;
        double ldcs, ldca;
        double cyl_x;
        double cyl_y;
        double cyl_blur;
     
        int n; double r[4];
    } Variables;
     
    // (SDK header apoplugin.h implied)
     
    APO_PLUGIN("dc_cylinder");
     
    APO_VARIABLES(
        
        VAR_REAL(dc_cyl_offset, 0.0),
        VAR_REAL(dc_cyl_angle,  0.0),
        VAR_REAL(dc_cyl_scale,  0.5),
        VAR_REAL(cyl_x, 0.125),
        VAR_REAL(cyl_y, 0.125),
        VAR_REAL(cyl_blur, 1.0),
        
    );
     
    int PluginVarPrepare(Variation* vp)
    {
        VAR(n) = 0;
        VAR(r)[0] = random01();
        VAR(r)[1] = random01();
        VAR(r)[2] = random01();
        VAR(r)[3] = random01();
        VAR(ldcs) = 1.0 / (VAR(dc_cyl_scale) == 0.0 ? 10E-6 : VAR(dc_cyl_scale));
    VAR(ldca) = VAR(dc_cyl_offset) * M_PI;
     
        return TRUE;
    }
     
    int PluginVarCalc(Variation* vp)
    {
        double r, sr, cr;
     
        fsincos(random01() * M_2PI, &sr, &cr);
        r = VAR(cyl_blur) * (VAR(r)[0] + VAR(r)[1] + VAR(r)[2] + VAR(r)[3] - 2.0);
        VAR(r)[VAR(n)] = random01();
        VAR(n) = VAR(n) + 1 & 3;
       
        FPx += VVAR * sin(FTx + r * sr)* VAR(cyl_x);
        FPy += r + FTy * VAR(cyl_y);
        FPz += VVAR * cos(FTx + r * cr);
        
         double c, s; fsincos(VAR(dc_cyl_angle), &s, &c);
    TC   = fmod( fabs( 0.5 * (VAR(ldcs) * ((c * FPx + s * FPy + VAR(dc_cyl_offset))) + 1.0) ), 1.0 );
       
        return TRUE;
    }
