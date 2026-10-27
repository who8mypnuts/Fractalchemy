/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/nBlur.c
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
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
*/

typedef struct
{
    
    int nb_numEdges, nb_numStripes;
    double nb_ratioStripes, nb_ratioComplement;
    int nb_equalBlur;
    double nb_ratioHole;
    int nb_exactCalc;
    int nb_adjustToLinear;
    int nb_circumCircle;
    double nb_highlightEdges;    
    double midAngle, angStripes, angStart;
    double tan90_m_2, sina, cosa;
    int hasStripes, negStripes;
    //**********Variables for speed up***********
    double speedCalc1, speedCalc2;
    double maxStripes;
    double arc_tan1, arc_tan2;
    
        
} Variables;

// (SDK header apoplugin.h implied)


APO_PLUGIN("nBlur");

APO_VARIABLES(
    
    VAR_INTEGER(nb_numEdges, 3),
    VAR_INTEGER(nb_numStripes, 0),
    VAR_REAL_RANGE(nb_ratioStripes, 0.0, 2.0, 1.0),
    VAR_REAL_RANGE(nb_ratioHole, 0.0, 1.0, 0.0),
    VAR_INTEGER_RANGE(nb_circumCircle, FALSE, TRUE, FALSE),
    VAR_INTEGER_RANGE(nb_adjustToLinear, FALSE, TRUE, TRUE),
    VAR_INTEGER_RANGE(nb_equalBlur, FALSE, TRUE, TRUE),
    VAR_INTEGER_RANGE(nb_exactCalc, FALSE, TRUE, FALSE),
    VAR_REAL(nb_highlightEdges, 1.0)
    
        
);


int PluginVarPrepare(Variation* vp)
{
    //**********Prepare edge related stuff***********
    if(VAR(nb_numEdges)<3) VAR(nb_numEdges) = 3;
    
    //*********Prepare stripes related stuff*********
    if(VAR(nb_numStripes)!=0)
    {
        VAR(hasStripes) = TRUE;
        if(VAR(nb_numStripes)<0)
        {
            VAR(negStripes) = TRUE;
            VAR(nb_numStripes) *= -1;
        }
        else
        {
            VAR(negStripes) = FALSE;
        }
    }
    else
    {
        VAR(hasStripes) == FALSE;
        VAR(negStripes) == FALSE;
    }

    //**********Prepare angle related stuff**********
    VAR(midAngle)   = M_2PI / (double)VAR(nb_numEdges);
    if(VAR(hasStripes)==TRUE)
    {
        VAR(angStripes)      = VAR(midAngle)/(double)(2*VAR(nb_numStripes));
        VAR(angStart)        = VAR(angStripes)/2.0;
        VAR(nb_ratioComplement) = 2.0 - VAR(nb_ratioStripes);
    }
    
    //**********Prepare hole related stuff***********
    if((VAR(nb_ratioHole)>0.95)&&(VAR(nb_exactCalc)==TRUE)&&(VAR(nb_circumCircle)==FALSE)) VAR(nb_ratioHole) = 0.95;
    
    //*********Prepare edge calculation related stuff*********
    VAR(tan90_m_2)  = tan(M_PI_2 + VAR(midAngle) / 2.0);
    fsincos((VAR(midAngle)/2.0), &VAR(sina), &VAR(cosa));
    
    //*********Prepare factor of adjustment of interpolated calculation*********
    if(VAR(nb_highlightEdges)<=0.1) VAR(nb_highlightEdges) = 0.1;
    
    //*********Adjustment of width of shape*********
    if(VAR(nb_adjustToLinear)==TRUE)
    {
        if((VAR(nb_numEdges)%4)==0)
        {
            VVAR /= sqrt(2.0 - 2.0 * cos(VAR(midAngle)*((double)VAR(nb_numEdges)/2.0-1.0)))/2.0;
        }
        else
        {
            VVAR /= sqrt(2.0 - 2.0 * cos(VAR(midAngle)*floor(((double)VAR(nb_numEdges)/2.0))))/2.0;
        }
    }
    
    //*********Prepare circumCircle-calculation*********
    if(VAR(nb_circumCircle)==TRUE)
    {
        VAR(nb_exactCalc)==FALSE;
        VAR(nb_highlightEdges) = 0.1;
    }
    
    //*********Prepare speed up related stuff*********
    VAR(speedCalc1) = VAR(nb_ratioComplement)*VAR(angStart);
    VAR(speedCalc2) = VAR(nb_ratioStripes)*VAR(angStart);
    VAR(maxStripes) = 2*VAR(nb_numStripes);
    if(VAR(negStripes)==FALSE)
    {
        VAR(arc_tan1) = (13.0/pow(VAR(nb_numEdges),1.3))*VAR(nb_highlightEdges);
        VAR(arc_tan2) = (2.0*atan(VAR(arc_tan1)/(-2.0)));
    }
    else
    {
        VAR(arc_tan1) = (7.5/pow(VAR(nb_numEdges),1.3))*VAR(nb_highlightEdges);
        VAR(arc_tan2) = (2.0*atan(VAR(arc_tan1)/(-2.0)));
    }
    
    return TRUE; 
}

int PluginVarCalc(Variation* vp)
{
    double x, y;
    double xTmp, yTmp, lenOuterEdges, lenInnerEdges;
    double angXY, lenXY;
    double ranTmp, angTmp, angMem, rotTmp;
    double ratioTmp, ratioTmpNum, ratioTmpDen, step;
    double speedCalcTmp;
    int    count;

    void randXY()
    {
        if(VAR(nb_exactCalc)==TRUE)
        {
            angXY = random01() * M_2PI;
        }
        else
        {
            angXY = (atan(VAR(arc_tan1)*(random01()-0.5))/VAR(arc_tan2)+0.5 + (double)(rand()%VAR(nb_numEdges))) * VAR(midAngle) ;
        }
        fsincos(angXY, &x, &y);
        angMem = angXY;
     
        while(angXY>VAR(midAngle))
        {
            angXY -= VAR(midAngle);
        }
        
        //********Begin of xy-calculation of radial stripes******** 
        if(VAR(hasStripes)==TRUE)
        {
            angTmp = VAR(angStart);
            count = 0;
            
            while(angXY>angTmp)
            {
                angTmp += VAR(angStripes);
                if(angTmp>VAR(midAngle)) angTmp = VAR(midAngle);
                count++;
            }
            
            if(angTmp!=VAR(midAngle)) angTmp -= VAR(angStart);
            
            if(VAR(negStripes)==FALSE)
            {
                if((count%2)==1)
                {
                    if(angXY>angTmp)
                    {
                        angXY =  angXY + VAR(angStart);
                        angMem = angMem + VAR(angStart);
                        fsincos(angMem, &x, &y);
                        angTmp += VAR(angStripes);
                        count++;
                    }
                    else
                    {
                        angXY  = angXY - VAR(angStart);
                        angMem = angMem - VAR(angStart);
                        fsincos(angMem, &x, &y);
                        angTmp -= VAR(angStripes);
                        count--;
                    }
                }
                if(((count%2)==0)&&(VAR(nb_ratioStripes)>1.0))
                {
                    if((angXY>angTmp)&&(count!=VAR(maxStripes)))
                    {
                        angMem = angMem - angXY + angTmp + (angXY-angTmp)/VAR(angStart) * VAR(nb_ratioStripes) * VAR(angStart);
                        angXY  = angTmp + (angXY-angTmp)/VAR(angStart) * VAR(nb_ratioStripes) * VAR(angStart);
                        fsincos(angMem, &x, &y);
                    }
                    else
                    {
                        angMem = angMem - angXY + angTmp - (angTmp-angXY)/VAR(angStart) * VAR(nb_ratioStripes) * VAR(angStart);
                        angXY  = angTmp + (angXY-angTmp)/VAR(angStart) * VAR(nb_ratioStripes) * VAR(angStart);
                        fsincos(angMem, &x, &y);
                    }
                }
                if(((count%2)==0)&&(VAR(nb_ratioStripes)<1.0))
                {
                    if((fabs(angXY-angTmp)>VAR(speedCalc2))&&(count!=(VAR(maxStripes))))
                    {
                        if((angXY-angTmp)>VAR(speedCalc2))
                        {
                            ratioTmpNum = (angXY-(angTmp+VAR(speedCalc2)))*VAR(speedCalc2);
                            ratioTmpDen = VAR(angStart)-VAR(speedCalc2);
                            ratioTmp    = ratioTmpNum/ratioTmpDen;
                            fsincos((angMem-angXY+angTmp+ratioTmp), &x, &y);
                            angXY = angTmp + ratioTmp;
                        }
                        if((angTmp-angXY)>VAR(speedCalc2))
                        {
                            ratioTmpNum = ((angTmp-VAR(speedCalc2)-angXY))*VAR(speedCalc2);
                            ratioTmpDen = VAR(angStart)-VAR(speedCalc2);
                            ratioTmp    = ratioTmpNum/ratioTmpDen;
                            fsincos((angMem-angXY+angTmp-ratioTmp), &x, &y);
                            angXY = angTmp - ratioTmp;
                        }
                    }
                    if(count==VAR(maxStripes))
                    {
                        if((angTmp-angXY)>VAR(speedCalc2))
                        {
                            ratioTmpNum = ((angTmp-VAR(speedCalc2)-angXY))*VAR(speedCalc2);
                            ratioTmpDen = VAR(angStart)-VAR(speedCalc2);
                            ratioTmp    = ratioTmpNum/ratioTmpDen;
                            fsincos((angMem-angXY+angTmp-ratioTmp), &x, &y);
                            angXY = angTmp - ratioTmp;
                        }
                    }
                }
            }
            else
            {
                //********Change ratio and ratioComplement******** 
                ratioTmp = VAR(nb_ratioStripes);
                VAR(nb_ratioStripes) = VAR(nb_ratioComplement);
                VAR(nb_ratioComplement) = ratioTmp;
                speedCalcTmp = VAR(speedCalc1);
                VAR(speedCalc1) = VAR(speedCalc2);
                VAR(speedCalc2) = speedCalcTmp;
                //************************************************ 
                if((count%2)==0)
                {
                    if((angXY>angTmp)&&(count!=VAR(maxStripes)))
                    {
                        angXY =  angXY + VAR(angStart);
                        angMem = angMem + VAR(angStart);
                        fsincos(angMem, &x, &y);
                        angTmp += VAR(angStripes);
                        count++;
                    }
                    else
                    {
                        angXY  = angXY - VAR(angStart);
                        angMem = angMem - VAR(angStart);
                        fsincos(angMem, &x, &y);
                        angTmp -= VAR(angStripes);
                        count--;
                    }
                }
                if(((count%2)==1)&&(VAR(nb_ratioStripes)>1.0))
                {
                    if((angXY>angTmp)&&(count!=VAR(maxStripes)))
                    {
                        angMem = angMem - angXY + angTmp + (angXY-angTmp)/VAR(angStart) * VAR(nb_ratioStripes) * VAR(angStart);
                        angXY  = angTmp + (angXY-angTmp)/VAR(angStart) * VAR(nb_ratioStripes) * VAR(angStart);
                        fsincos(angMem, &x, &y);
                    }
                    else
                    {
                        angMem = angMem - angXY + angTmp - (angTmp-angXY)/VAR(angStart) * VAR(nb_ratioStripes) * VAR(angStart);
                        angXY  = angTmp + (angXY-angTmp)/VAR(angStart) * VAR(nb_ratioStripes) * VAR(angStart);
                        fsincos(angMem, &x, &y);
                    }
                }
                if(((count%2)==1)&&(VAR(nb_ratioStripes)<1.0))
                {
                    if((fabs(angXY-angTmp)>VAR(speedCalc2))&&(count!=VAR(maxStripes)))
                    {
                        if((angXY-angTmp)>VAR(speedCalc2))
                        {
                            ratioTmpNum = (angXY-(angTmp+VAR(speedCalc2)))*VAR(speedCalc2);
                            ratioTmpDen = VAR(angStart)-VAR(speedCalc2);
                            ratioTmp    = ratioTmpNum/ratioTmpDen;
                            fsincos((angMem-angXY+angTmp+ratioTmp), &x, &y);
                            angXY = angTmp + ratioTmp;
                        }
                        if((angTmp-angXY)>VAR(speedCalc2))
                        {
                            ratioTmpNum = ((angTmp-VAR(speedCalc2)-angXY))*VAR(speedCalc2);
                            ratioTmpDen = VAR(angStart)-VAR(speedCalc2);
                            ratioTmp    = ratioTmpNum/ratioTmpDen;
                            fsincos((angMem-angXY+angTmp-ratioTmp), &x, &y);
                            angXY = angTmp - ratioTmp;
                        }
                    }
                    if(count==VAR(maxStripes))
                    {
                        angTmp = VAR(midAngle);
                        if((angTmp-angXY)>VAR(speedCalc2))
                        {
                            ratioTmpNum = ((angTmp-VAR(speedCalc2)-angXY))*VAR(speedCalc2);
                            ratioTmpDen = VAR(angStart)-VAR(speedCalc2);
                            ratioTmp    = ratioTmpNum/ratioTmpDen;
                            fsincos((angMem-angXY+angTmp-ratioTmp), &x, &y);
                            angXY = angTmp - ratioTmp;
                        }
                    }
                }
                //********Restore ratio and ratioComplement******* 
                ratioTmp = VAR(nb_ratioStripes);
                VAR(nb_ratioStripes) = VAR(nb_ratioComplement);
                VAR(nb_ratioComplement) = ratioTmp;
                speedCalcTmp = VAR(speedCalc1);
                VAR(speedCalc1) = VAR(speedCalc2);
                VAR(speedCalc2) = speedCalcTmp;
                //************************************************ 
            }
        }
        //********End of xy-calculation of radial stripes********
        
        //********Begin of calculation of edge limits********
        xTmp = VAR(tan90_m_2) / (VAR(tan90_m_2) - tan(angXY));
        yTmp = xTmp * tan(angXY);    
        lenOuterEdges = sqrt(xTmp*xTmp+yTmp*yTmp);
         //*********End of calculation of edge limits********
        
        //********Begin of radius-calculation (optionally hole)********
        if(VAR(nb_exactCalc)==TRUE)
        {
            if(VAR(nb_equalBlur)==TRUE) ranTmp = sqrt(random01());
            else                        ranTmp = random01();
        }
        else
        {
            if(VAR(nb_circumCircle)==TRUE)
            {
                if(VAR(nb_equalBlur)==TRUE) ranTmp = sqrt(random01());
                else                        ranTmp = random01();
            }
            else
            {
                if(VAR(nb_equalBlur)==TRUE) ranTmp = sqrt(random01()) * lenOuterEdges;
                else                        ranTmp = random01() * lenOuterEdges;
            }
        }
        lenInnerEdges = VAR(nb_ratioHole)*lenOuterEdges;

        if(VAR(nb_exactCalc)==FALSE)
        {
            if(ranTmp<lenInnerEdges)
            {
                if(VAR(nb_circumCircle)==TRUE)
                {
                    if(VAR(nb_equalBlur==TRUE)) ranTmp = lenInnerEdges + sqrt(random01()) * (1.0 - lenInnerEdges + EPS);
                    else                        ranTmp = lenInnerEdges + random01() * (1.0 - lenInnerEdges + EPS);
                }
                else
                {
                    if(VAR(nb_equalBlur==TRUE)) ranTmp = lenInnerEdges + sqrt(random01()) * (lenOuterEdges - lenInnerEdges);
                    else                        ranTmp = lenInnerEdges + random01()       * (lenOuterEdges - lenInnerEdges);
                }
            }
        }
       
        //if(VAR(hasStripes)==TRUE) ranTmp = pow(ranTmp,0.75);
        x *= ranTmp;
        y *= ranTmp;
        lenXY = sqrt(x*x+y*y);
        //*********End of radius-calculation (optionally hole)*********
    }
    
    randXY();

    //********Exact calculation slower - interpolated calculation faster********
    if((VAR(nb_exactCalc)==TRUE)&&(VAR(nb_circumCircle)==FALSE))
    {
        while((lenXY<lenInnerEdges)||(lenXY>lenOuterEdges)) randXY();    
    }
    if((VAR(nb_exactCalc)==TRUE)&&(VAR(nb_circumCircle)==TRUE))
    {
        while(lenXY<lenInnerEdges) randXY();    
    }
    xTmp = x;
    yTmp = y;
    
    //**************************************************************************
    
    //********Begin of horizontal adjustment (rotation)********
    x = VAR(cosa)*xTmp - VAR(sina)*yTmp;
    y = VAR(sina)*xTmp + VAR(cosa)*yTmp;
    //*********End of horizontal adjustment (rotation)*********
    
    FPx += VVAR * x;
    FPy += VVAR * y;

    return TRUE;
}
