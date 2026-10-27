/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        minkowskope.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
*/

// Must define this structure before we include apoplugin.h
typedef struct
{
    double mskope_separation;
    double mskope_frequencyx;
    double mskope_frequencyy;
    double mskope_amplitude;
    double mskope_perturbation;
    double mskope_damping;
    // --------------------------
    double _tpf,_tpf2;
    int _noDamping,_altWave;
} Variables;

// (SDK header apoplugin.h implied)
double minkosine(double x, int awv) ;
double minkocosine(double x, int awv) ;
double minkowski(double x);

// Set the name of this plugin
APO_PLUGIN("minkowskope");

// Define the Variables
APO_VARIABLES(
    VAR_REAL(mskope_separation, 1.0),
    VAR_REAL(mskope_frequencyx, M_PI),
    VAR_REAL(mskope_frequencyy, M_PI),
    VAR_REAL(mskope_amplitude, 1.0),
    VAR_REAL(mskope_perturbation, 1.0),
    VAR_REAL(mskope_damping, 0.0)
);


int PluginVarPrepare(Variation* vp)
{
    VAR(_tpf) = 0.5 * VAR(mskope_frequencyx);
    VAR(_tpf2) = 0.5 * VAR(mskope_frequencyy);
    VAR(_noDamping) = fabs(VAR(mskope_damping)) <= EPS;
    VAR(_altWave) = VAR(mskope_frequencyx) <= 0.0;
    return TRUE;
}

double minkosine(double x, int awv) {
    double lp = fmod(fabs(x) , 4.);
    double p = fmod(fabs(x) , 2.);
    double mink = 0;
    if (p>1.) p = 2.-p; // sawtooth wave
    if (awv)
        mink = minkowski(p) - p; // cool looking (uses a different waveform)
    else
        mink = minkowski(p); // normal :P
    if ((lp<2.) ^ (x > 0)) return mink; // lol!!! xor
    else return -mink;
}

double minkocosine(double x, int awv) {
    return minkosine(x-1., awv);
}

/* Minkowski's question mark function from Wikipedia, adapted
DO NOT! call it directly it is ... weird, use minkosine or minkocosine thanks!
 */
double minkowski(double x) {
    /* double p=(long)x;
    if (p>x) p = p - 1.; */
    double p = 0.; // d'oh
    double q=1., r=p+1., s=1., m=0., n=0.;
    double d=1., y=p;
    int it = 0;
    for ( ; it < 20; it++) // precision 1e-6
    {
            d=d*0.5; //if (d<1e-10) break;
            m=p+r;
            n=q+s;
            if (x<(m/n)) {
                r=m; s=n;
                }
            else {
                y+=d; p=m; q=n;
                }
    }
    return y+d;
}

int PluginVarCalc(Variation* vp)
{
    double t;
    double pt = VAR(mskope_perturbation) * minkosine(VAR(_tpf2) * FTy, VAR(_altWave));
    if (VAR(_noDamping)) {
      t = VAR(mskope_amplitude) * (minkocosine(VAR(_tpf) * FTx + pt, VAR(_altWave))) + VAR(mskope_separation);
    }
    else {
      t = VAR(mskope_amplitude) * exp(-fabs(FTx) * VAR(mskope_damping)) * (minkocosine(VAR(_tpf) * FTx + pt,VAR(_altWave))) + VAR(mskope_separation);
    }

    if(fabs(FTy) <= t)
    {
       FPx -= VVAR*FTx;
       FPy -= VVAR*FTy;
    }
    else
    {
       FPx += VVAR*FTx;
       FPy += VVAR*FTy;
    }
    return TRUE;
}

