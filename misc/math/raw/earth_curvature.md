---
title: "Earth's Curvature"
author: "Jamie Breault"
header-includes: |
  \usepackage{tikz}
  \usetikzlibrary{calc,angles,quotes,arrows.meta}
---

This document derives the geometry used to place a sampled point into the two-dimensional vertical cross-section that line-of-sight analysis works in (see `LineOfSight.process_full_line_of_sight` in `scripts/commons.py`).

A point sits at surface distance $D_s$ from the observer (measured along the surface of the Earth at sea level) and at elevation $h$ above sea level. We want its position relative to the observer's horizontal plane.

**Notation**

- $R_\oplus$ — mean radius of the Earth at sea level.
- $D_s$ — surface distance between the observer and the point.
- $\theta$ — central angle between the observer and the point, $\theta = D_s / R_\oplus$.
- $D_x$ — horizontal distance from the observer to the point's projection on the observer's horizontal plane.
- $D_y$ — vertical distance of the point above the observer's horizontal plane.
- $\alpha$ — angle between the observer's horizontal plane and the straight line to the point.

---

\begin{center}
\begin{tikzpicture}[scale=1.05,>=Latex]
  \def\R{5}\def\th{50}
  \coordinate (C) at (0,0);
  \coordinate (O) at (0,\R);
  \coordinate (T) at ({\R*sin(\th)},{\R*cos(\th)});
  \coordinate (P) at ({\R*sin(\th)},\R);
  % Earth surface arc
  \draw[thick] ({\R*cos(125)},{\R*sin(125)}) arc (125:40:\R);
  \node at (-2.35,5.25) {Earth};
  % surface distance label, clearly above the arc on the right side
  \node at (2.6,4.72) {$D_s$};
  % radii
  \draw[dashed] (C) -- (O);
  \draw[dashed] (C) -- (T) node[pos=0.62,below right] {$R_\oplus$};
  \pic[draw,"$\theta$",angle radius=1cm,angle eccentricity=1.5]{angle=T--C--O};
  % observer horizontal plane + curvature drop
  \draw[->] (O) -- (P) node[midway,above] {$D_x$};
  \draw[->] (P) -- (T) node[midway,right] {$D_y$};
  % direct (chord) line
  \draw (O) -- (T) node[pos=0.5,below left] {$D_d$};
  \pic[draw,"$\alpha$",angle radius=1.0cm,angle eccentricity=1.75]{angle=T--O--P};
  % points
  \fill (O) circle (1.4pt) node[above=2pt] {$O$};
  \fill (T) circle (1.4pt) node[below right] {$T$};
  \fill (C) circle (1.4pt) node[below] {centre};
\end{tikzpicture}
\end{center}

\noindent\emph{Geometry of a point at central angle $\theta$ from the observer $O$, relative to $O$'s horizontal plane.}

Horizontal distance:
$$\sin(\theta) = D_x / R_\oplus \implies D_x = R_\oplus \sin\!\left(\frac{D_s}{R_\oplus}\right)$$

Vertical drop due to curvature:
$$R_\oplus = R_\oplus \cos(\theta) + D_y \implies D_y = R_\oplus \left(1 - \cos\!\left(\frac{D_s}{R_\oplus}\right)\right)$$

Angle below the horizontal plane:
$$\tan(\alpha) = \frac{D_y}{D_x} = \frac{1 - \cos(D_s/R_\oplus)}{\sin(D_s/R_\oplus)} = \tan\!\left(\frac{D_s}{2 R_\oplus}\right)$$
$$\alpha = \frac{D_s}{2 R_\oplus}, \quad 0 < \alpha < \pi/2$$

A point at elevation $h$ lies at radius $R_\oplus + h$, so its Cartesian position (observer at the origin) is
$$x = (R_\oplus + h)\sin\theta, \qquad y = (R_\oplus + h)\cos\theta - R_\oplus - h_1,$$
where $h_1$ is the observer's elevation. The cross-section is then rotated by $\alpha$ so the straight observer-target line lies on the x-axis, making ground heights directly comparable to the light-ray heights derived in `atmospheric_refraction.md`.
