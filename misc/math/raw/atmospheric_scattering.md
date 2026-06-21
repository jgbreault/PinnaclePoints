---
title: "Atmospheric Scattering"
author: "Jamie Breault"
header-includes: |
  \usepackage{tikz}
  \usetikzlibrary{calc,angles,quotes,arrows.meta}
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

**Choosing $S$ and $a$.** The shaded segment is the near, observer-side half of the path ($S = 0.5$), because airlight is dominated by the air closest to the observer, so shadowing it helps contrast most. The shade irradiation ratio $a$ is set per line of sight from its bearing, to approximate sunrise/sunset. The sun can only rise or set along the east-west horizon, so only an east-west sightline can place the observer's foreground in shadow with the target lit beyond; a north-south sightline has the sun broadside and gets no benefit. Hence $a = 1 - (1 - a_{\min})\,|\sin(\text{bearing})|$ with $a_{\min} = 0.1$: east-west gives $a = 0.1$ (deepest shadow, highest contrast), north-south gives $a = 1$ (plain extinction), and bearings between interpolate. $a_{\min}$ stays above $0$ because fully shadowed air is still lit by diffuse skylight.

**Irradiation by bearing.** The table below evaluates $a = 1 - (1 - a_{\min})\,|\sin(\text{bearing})|$ at $15^\circ$ steps, alongside the resulting reduction in shaded-segment irradiation, $1 - a = (1 - a_{\min})\,|\sin(\text{bearing})|$. Because the relation depends on $|\sin(\text{bearing})|$, it is symmetric every $180^\circ$: the reduction is largest ($1 - a = 0.9$) for east-west sightlines and vanishes for north-south ones.

| Bearing | Reduction ($1 - a$) | Irradiation ($a$) |
|:-------:|:-------------------:|:-----------------:|
| $0^\circ$ (N)   | 0.000 | 1.000 |
| $15^\circ$      | 0.233 | 0.767 |
| $30^\circ$      | 0.450 | 0.550 |
| $45^\circ$      | 0.636 | 0.364 |
| $60^\circ$      | 0.779 | 0.221 |
| $75^\circ$      | 0.869 | 0.131 |
| $90^\circ$ (E)  | 0.900 | 0.100 |
| $105^\circ$     | 0.869 | 0.131 |
| $120^\circ$     | 0.779 | 0.221 |
| $135^\circ$     | 0.636 | 0.364 |
| $150^\circ$     | 0.450 | 0.550 |
| $165^\circ$     | 0.233 | 0.767 |
| $180^\circ$ (S) | 0.000 | 1.000 |
| $195^\circ$     | 0.233 | 0.767 |
| $210^\circ$     | 0.450 | 0.550 |
| $225^\circ$     | 0.636 | 0.364 |
| $240^\circ$     | 0.779 | 0.221 |
| $255^\circ$     | 0.869 | 0.131 |
| $270^\circ$ (W) | 0.900 | 0.100 |
| $285^\circ$     | 0.869 | 0.131 |
| $300^\circ$     | 0.779 | 0.221 |
| $315^\circ$     | 0.636 | 0.364 |
| $330^\circ$     | 0.450 | 0.550 |
| $345^\circ$     | 0.233 | 0.767 |
| $360^\circ$ (N) | 0.000 | 1.000 |
