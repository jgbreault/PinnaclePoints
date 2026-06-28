---
title: "Atmospheric Scattering"
author: "Jamie Breault"
header-includes: |
  \usepackage{tikz}
  \usetikzlibrary{calc,angles,quotes,arrows.meta}
  \usepackage{booktabs}
  \usepackage{graphicx}
---

A geometrically unobstructed line of sight is not enough for the target to be visible: air scatters light, so a distant target fades into the background sky. This document assembles the **contrast** of the target against the sky, following Michael Vollmer, *Below the horizon — the physics of extreme visual ranges* (2020). The target is considered visible when its contrast exceeds $0.02$, the threshold of human vision. This is computed in `LineOfSight.get_contrast` and `LineOfSight.has_contrast` in `scripts/commons.py`.

In polar coordinates the observer is at $P_1 = (R_\oplus + h_1,\, 0)$ and the target at $P_2 = (R_\oplus + h_2,\, D_s/R_\oplus)$. Light follows the arc of a circle of radius $R_L = k R_\oplus$ (see `atmospheric_refraction.md`).

**Notation**

- $C$ — contrast of the target against the sky.
- $h_1, h_2$ — elevation of the observer and target.
- $D_s$ — surface (sea-level arc) distance between observer and target.
- $D_d$ — direct (straight-line) distance between observer and target.
- $H$ — scale height of the atmosphere.
- $\beta_0$ — scattering coefficient at sea level.
- $\beta(h) = \beta_0\, e^{-h/H}$ — scattering coefficient at elevation $h$.
- $\beta_1, \beta_2$ — average scattering coefficient over the shaded and sunlit segments.
- $S$ — shaded ratio: fraction of the path in shadow, starting at the observer.
- $a$ — shade irradiation ratio: brightness of the shaded segment relative to the sunlit segment.
- $\varepsilon = 23.44^\circ$ — Earth's axial tilt.
- $\Delta$ — half-width of the sunrise (and sunset) azimuth range at the observer's latitude.
- $\beta$ — observer-to-target bearing, measured clockwise from North ($0^\circ$–$360^\circ$).
- $\alpha^\star$ — optimal sun azimuth: the nearest achievable sunrise or sunset azimuth to $\beta$.
- $\delta$ — angular deviation of $\beta$ from $\alpha^\star$.
- $x$ — surface distance from the observer; $\theta = x/R_\oplus$, $\phi = D_s/R_\oplus$.
- $L(x)$ — distance from the centre of the Earth to the light arc at $x$.
- $h(x) = L(x) - R_\oplus$ — height of the light arc above sea level at $x$.
- $(M_x, M_y)$ — centre of the light-arc circle in Cartesian coordinates.

---

\begin{center}
\begin{tikzpicture}[scale=1.05,>=Latex]
  \def\W{8}
  % light path as a circular arc (centre (4,-7.5), R=8.5), like the refraction figure
  \draw[thick] (0,0) arc (118.06:61.93:8.5);
  \node at (1.5,1.0) {Light};
  % endpoints
  \fill (0,0) circle (1.5pt) node[left] {$O$};
  \fill (\W,0) circle (1.5pt) node[right] {$T$};
  % shadow boundary
  \draw[dashed] (4,-0.5) -- (4,2.05) node[above,align=center] {shadow\\boundary};
  % segment labels
  \draw[<->] (0,-0.95) -- (4,-0.95) node[midway,below,align=center] {shaded $d_1=SD_s$\\(irradiation $a$)};
  \draw[<->] (4,-0.95) -- (\W,-0.95) node[midway,below,align=center] {sunlit $d_2=(1-S)D_s$};
  % sun low to the right
  \coordinate (SUN) at ({\W+1.7},2.8);
  \draw (SUN) circle (0.35);
  \node at ({\W+1.7},3.4) {Sun};
  % rays reaching the sunlit segment only (blocked at the shadow boundary)
  \draw[->] (SUN) -- (5.5,0.866);
  \draw[->] (SUN) -- (6.4,0.654);
  \draw[->] (SUN) -- (7.3,0.333);
  % notes
  \node at (2,1.7) {dimmed airlight};
  \node at (6,1.7) {full airlight};
\end{tikzpicture}
\end{center}

\noindent\emph{Partial irradiation: near sunrise/sunset the observer-side half of the path lies in shadow (dimmed airlight, irradiation ratio $a$), while the target-side half is still sunlit. Shadowing the near air, where airlight is strongest, is what lets extreme sightlines keep contrast.}

**Contrast** (Vollmer eq. 9). The path is split into a shaded segment of length $d_1 = S D_s$ (starting at the observer) and a sunlit segment of length $d_2 = (1 - S) D_s$:

$$C = \frac{e^{-\beta_2 d_2}}{1 - a + \left( \dfrac{a}{e^{-\beta_1 d_1}} \right)}$$

**Average scattering coefficients** (Vollmer eq. 7). Scattering thins with altitude, so the sea-level coefficient is weighted by the height of the light path and integrated along it. The integrals run over the light path, with arc-length element $ds$:

$$\beta_1 = \frac{\beta_0}{d_1}\int_{0}^{d_1} e^{-h(x)/H}\,ds, \qquad \beta_2 = \frac{\beta_0}{d_2}\int_{d_1}^{D_s} e^{-h(x)/H}\,ds$$
$$d_1 = S D_s, \qquad d_2 = (1 - S) D_s, \qquad h(x) = L(x) - R_\oplus$$

Here $ds$ is the arc-length element of the light path. Parameterising by surface distance $x$ (so $\theta = x/R_\oplus$), $ds = \sqrt{(L/R_\oplus)^2 + (dL/dx)^2}\,dx \approx (L/R_\oplus)\,dx$, so in code the surface-distance integral is weighted by $L/R_\oplus$ (see `LineOfSight.get_contrast`).

**Height of the light arc.** With $\theta = x/R_\oplus$, the light circle in polar form is

$$L(x) = M_x\cos\theta + M_y\sin\theta + \sqrt{(M_x\cos\theta + M_y\sin\theta)^2 + R_L^2 - M_x^2 - M_y^2}$$

where the centre of the light circle and the endpoints are

$$M_x = \frac{x_1 + x_2}{2} - Z\,\frac{y_2 - y_1}{D_d}, \qquad M_y = \frac{y_1 + y_2}{2} + Z\,\frac{x_2 - x_1}{D_d}, \qquad Z = \sqrt{R_L^2 - \left(\frac{D_d}{2}\right)^2}$$
$$P_1 = (x_1, y_1) = (R_\oplus + h_1,\; 0), \qquad P_2 = (x_2, y_2) = \big((R_\oplus + h_2)\cos\phi,\; (R_\oplus + h_2)\sin\phi\big)$$
$$D_d = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}, \qquad \phi = \frac{D_s}{R_\oplus}$$

**Choosing $S$ and $a$.** The shaded segment is the near, observer-side half of the path ($S = 0.5$), because airlight is dominated by the air closest to the observer, so shadowing it helps contrast most. The shade irradiation ratio $a$ is set per line of sight from its bearing, modelling the most favourable sunrise or sunset alignment achievable on any day of the year. $a_{\min} = 0.1$ stays above $0$ because even fully shadowed air is still lit by diffuse skylight.

**Optimal sun azimuth.** The sun does not always rise due east. At the observer's latitude $\varphi$, the sunrise azimuth ranges between $90^\circ - \Delta$ and $90^\circ + \Delta$ from North over the course of a year, where

$$\Delta = \arcsin\!\left(\frac{\sin\varepsilon}{\cos\varphi}\right), \qquad \varepsilon = 23.44^\circ \text{ (Earth's axial tilt)}$$

$\Delta$ is capped at $90^\circ$ above the polar circles ($|\varphi| \geq 90^\circ - \varepsilon \approx 66.6^\circ$), where the sun can rise at any azimuth on some day of the year. The sunset range is the symmetric counterpart $[270^\circ - \Delta,\; 270^\circ + \Delta]$.

\begin{center}
\begin{tikzpicture}[scale=1.5, >=Latex]
  \def\R{1.5}
  \def\D{30}
  % Sunrise range: bearings [90-D, 90+D] => math angles [-D, D] (centred on East)
  \filldraw[fill=yellow!40, draw=orange!80, thick]
    (0,0) -- ({\R*cos(-\D)},{\R*sin(-\D)}) arc ({-\D}:{\D}:\R) -- cycle;
  % Sunset range: bearings [270-D, 270+D] => math angles [180-D, 180+D] (centred on West)
  \filldraw[fill=cyan!30, draw=blue!60, thick]
    (0,0) -- ({\R*cos(180-\D)},{\R*sin(180-\D)}) arc ({180-\D}:{180+\D}:\R) -- cycle;
  % Horizon circle
  \draw[thick] (0,0) circle (\R);
  % Faint cross-hairs
  \draw[gray!30] (-\R,0) -- (\R,0);
  \draw[gray!30] (0,-\R) -- (0,\R);
  % Cardinal labels (bearing convention: North up, East right)
  \node[font=\small] at (0,\R+0.28) {N ($0^\circ$)};
  \node[font=\small] at (\R+0.35,0) {E ($90^\circ$)};
  \node[font=\small] at (0,-\R-0.28) {S ($180^\circ$)};
  \node[font=\small] at (-\R-0.35,0) {W ($270^\circ$)};
  % Delta arc annotation on sunrise side
  \draw[<->, orange!80!black, thick] ({\R*0.5},0) arc (0:\D:{\R*0.5});
  \node[orange!80!black, font=\footnotesize] at ({\R*0.62*cos(\D/2)},{\R*0.62*sin(\D/2)+0.1}) {$\Delta$};
  % Range labels outside circle
  \node[orange!80!black, font=\footnotesize] at ({\R*1.5},0.15) {sunrise};
  \node[orange!80!black, font=\footnotesize] at ({\R*1.5},-0.15) {range};
  \node[blue!70!black, font=\footnotesize] at ({-\R*1.5},0.15) {sunset};
  \node[blue!70!black, font=\footnotesize] at ({-\R*1.5},-0.15) {range};
\end{tikzpicture}
\end{center}

\noindent\emph{Compass showing the sunrise (yellow) and sunset (blue) azimuth ranges at a mid-latitude observer ($\Delta \approx 30^\circ$, corresponding to $\varphi \approx 45^\circ$). Bearings inside either shaded wedge can be perfectly aligned with the sun on some day of the year.}

Let $d(\beta, \alpha) = \min(|\beta - \alpha|,\; 360^\circ - |\beta - \alpha|)$ be the circular angular distance between bearing $\beta$ and azimuth $\alpha$. The deviation of $\beta$ from the nearest sunrise or sunset range is

$$\delta_\text{rise} = \max\!\bigl(0,\; d(\beta,\, 90^\circ) - \Delta\bigr), \qquad \delta_\text{set} = \max\!\bigl(0,\; d(\beta,\, 270^\circ) - \Delta\bigr), \qquad \delta = \min(\delta_\text{rise},\; \delta_\text{set})$$

When $\delta = 0$ the bearing falls inside a sunrise or sunset range — the sun can rise or set exactly along that line of sight on some day of the year — so the full shadow benefit applies. The shade irradiation ratio is

$$\boxed{a = 1 - (1 - a_{\min})\cos\delta}$$

When $\delta = 0$: $a = a_{\min} = 0.1$ (deepest foreground shadow, highest contrast). When $\delta = 90^\circ$ (the bearing lies exactly between the sunrise and sunset ranges, i.e. due north or south): $a = 1$ (sun is broadside, no shadow benefit).

**Equivalence to the prior formula.** When $\varepsilon = 0$ (no axial tilt, sunrise always exactly due east), $\Delta = 0$, the ranges collapse to single azimuths at $90^\circ$ and $270^\circ$, $\delta = \min(d(\beta, 90^\circ), d(\beta, 270^\circ)) = 90^\circ - \bigl||\beta \bmod 180^\circ| - 90^\circ\bigr|$, and $\cos\delta = |\sin\beta|$, recovering the simpler approximation $a = 1 - (1 - a_{\min})|\sin\beta|$.

**Which range applies.** For the longest-line-of-sight search the observer is always the western summit, so the bearing is always roughly eastward and only $\delta_\text{rise}$ ever wins. For the pinnacle point search the candidate is the observer and the target can be in any direction, so both ranges are checked and the nearer one determines $\delta$.

```{=latex}
\newpage

\noindent\textbf{Sun azimuth offset $\delta$ (degrees) --- longest-line-of-sight search.}
The observer is always the western summit; only the sunrise range $[90^\circ - \Delta,\; 90^\circ + \Delta]$ applies.
Zero means the bearing falls within the achievable sunrise range at that latitude
(perfectly aligned with sunrise on some day of the year). The offset grows as the
bearing diverges from the east-facing corridor; north-south sightlines at the equator
reach the maximum of $90^\circ - \Delta \approx 66.6^\circ$.

\vspace{0.8em}
\renewcommand{\arraystretch}{1.25}
\noindent\resizebox{\textwidth}{!}{%
\begin{tabular}{l|rrrrrrr}
\toprule
\textbf{Bearing} $\beta$ & $\varphi=0^\circ$ & $\varphi=15^\circ$ & $\varphi=30^\circ$ & $\varphi=45^\circ$ & $\varphi=60^\circ$ & $\varphi=70^\circ$ & $\varphi=75^\circ$ \\
\midrule
  $0^\circ$ (N)   & 66.6 & 65.7 & 62.7 & 55.8 & 37.3 & 0 & 0 \\
  $15^\circ$      & 51.6 & 50.7 & 47.7 & 40.8 & 22.3 & 0 & 0 \\
  $30^\circ$      & 36.6 & 35.7 & 32.7 & 25.8 &  7.3 & 0 & 0 \\
  $45^\circ$      & 21.6 & 20.7 & 17.7 & 10.8 &    0 & 0 & 0 \\
  $60^\circ$      &  6.6 &  5.7 &  2.7 &    0 &    0 & 0 & 0 \\
  $75^\circ$      &    0 &    0 &    0 &    0 &    0 & 0 & 0 \\
  $90^\circ$ (E)  &    0 &    0 &    0 &    0 &    0 & 0 & 0 \\
  $105^\circ$     &    0 &    0 &    0 &    0 &    0 & 0 & 0 \\
  $120^\circ$     &  6.6 &  5.7 &  2.7 &    0 &    0 & 0 & 0 \\
  $135^\circ$     & 21.6 & 20.7 & 17.7 & 10.8 &    0 & 0 & 0 \\
  $150^\circ$     & 36.6 & 35.7 & 32.7 & 25.8 &  7.3 & 0 & 0 \\
  $165^\circ$     & 51.6 & 50.7 & 47.7 & 40.8 & 22.3 & 0 & 0 \\
  $180^\circ$ (S) & 66.6 & 65.7 & 62.7 & 55.8 & 37.3 & 0 & 0 \\
\midrule
  $\Delta$        & $23.4^\circ$ & $24.3^\circ$ & $27.3^\circ$ & $34.2^\circ$ & $52.7^\circ$ & $90^\circ$ & $90^\circ$ \\
\bottomrule
\end{tabular}}

\newpage

\noindent\textbf{Sun azimuth offset $\delta$ (degrees) --- pinnacle point search.}
The candidate is always the observer; the target can be in any direction, so both
the sunrise range $[90^\circ - \Delta,\; 90^\circ + \Delta]$ and the sunset range
$[270^\circ - \Delta,\; 270^\circ + \Delta]$ are checked and the smaller deviation wins.
Two corridors of zeros appear --- centred on east and west --- instead of the single
east-facing corridor of the longest-LOS search. The table is symmetric: bearings
$\beta$ and $360^\circ - \beta$ give identical offsets.

\vspace{0.8em}
\renewcommand{\arraystretch}{1.25}
\noindent\resizebox{\textwidth}{!}{%
\begin{tabular}{l|rrrrrrr}
\toprule
\textbf{Bearing} $\beta$ & $\varphi=0^\circ$ & $\varphi=15^\circ$ & $\varphi=30^\circ$ & $\varphi=45^\circ$ & $\varphi=60^\circ$ & $\varphi=70^\circ$ & $\varphi=75^\circ$ \\
\midrule
  $0^\circ$ (N)   & 66.6 & 65.7 & 62.7 & 55.8 & 37.3 & 0 & 0 \\
  $30^\circ$      & 36.6 & 35.7 & 32.7 & 25.8 &  7.3 & 0 & 0 \\
  $60^\circ$      &  6.6 &  5.7 &  2.7 &    0 &    0 & 0 & 0 \\
  $90^\circ$ (E)  &    0 &    0 &    0 &    0 &    0 & 0 & 0 \\
  $120^\circ$     &  6.6 &  5.7 &  2.7 &    0 &    0 & 0 & 0 \\
  $150^\circ$     & 36.6 & 35.7 & 32.7 & 25.8 &  7.3 & 0 & 0 \\
  $180^\circ$ (S) & 66.6 & 65.7 & 62.7 & 55.8 & 37.3 & 0 & 0 \\
  $210^\circ$     & 36.6 & 35.7 & 32.7 & 25.8 &  7.3 & 0 & 0 \\
  $240^\circ$     &  6.6 &  5.7 &  2.7 &    0 &    0 & 0 & 0 \\
  $270^\circ$ (W) &    0 &    0 &    0 &    0 &    0 & 0 & 0 \\
  $300^\circ$     &  6.6 &  5.7 &  2.7 &    0 &    0 & 0 & 0 \\
  $330^\circ$     & 36.6 & 35.7 & 32.7 & 25.8 &  7.3 & 0 & 0 \\
\midrule
  $\Delta$        & $23.4^\circ$ & $24.3^\circ$ & $27.3^\circ$ & $34.2^\circ$ & $52.7^\circ$ & $90^\circ$ & $90^\circ$ \\
\bottomrule
\end{tabular}}
```
