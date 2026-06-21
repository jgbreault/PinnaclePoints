---
title: "Atmospheric Refraction"
author: "Jamie Breault"
header-includes: |
  \usepackage{tikz}
  \usetikzlibrary{calc,angles,quotes,arrows.meta}
---

Atmospheric refraction bends light, so a light ray is modelled as the arc of a circle of radius $R_\text{light} = k\,R_\oplus$. This document derives the height of that arc above the straight observer-target line (used as `light_heights` in `LineOfSight.process_full_line_of_sight` in `scripts/commons.py`).

Work in the rotated frame from `earth_curvature.md`: the observer is at $(0, 0)$ and the target is at $(D_d, 0)$, where $D_d$ is the direct (straight-line) distance between them. Find $y$, the height of the light arc, in terms of $x$, $k$, $D_d$, and $R_\oplus$.

**Notation**

- $y$ — height of the light ray above the straight observer-target line.
- $x$ — horizontal distance along that straight line.
- $k$ — light curvature factor, $R_\text{light} = k R_\oplus$. Larger $k$ means straighter light.
- $D_d$ — direct (straight-line) distance between observer and target.
- $R_\oplus$ — mean radius of the Earth at sea level.

---

\begin{center}
\begin{tikzpicture}[scale=1.05,>=Latex]
  \def\Dd{6}
  \coordinate (O) at (0,0);
  \coordinate (T) at (\Dd,0);
  \coordinate (M) at (3,0);
  \coordinate (C) at (3,-3.15);
  \def\RL{4.35}
  % light arc
  \draw[thick] (O) arc (133.6:46.4:\RL);
  \node at (3,1.5) {Light};
  % chord / direct line
  \draw (O) -- (T);
  % radii (label hugs the line)
  \draw[dashed] (C) -- (O) node[midway,sloped,above=1pt] {$kR_\oplus$};
  \draw[dashed] (C) -- (T);
  % drop ell
  \draw[dashed] (M) -- (C);
  \node[right] at (3,-0.85) {$\ell$};
  % general point before halfway (x=2), keeping the ell side uncluttered
  \coordinate (Pf) at (2,0);
  \coordinate (P) at (2,1.0835);
  \draw[dashed] (Pf) -- (P) node[midway,left] {$y$};
  \fill (P) circle (1.2pt) node[above left] {$(x,\,y)$};
  \draw[<->] (0,-0.55) -- (2,-0.55) node[midway,below] {$x$};
  \draw[<->] (0,-1.35) -- (\Dd,-1.35) node[midway,below] {$D_d$};
  % points
  \fill (O) circle (1.4pt) node[above left] {$O=(0,0)$};
  \fill (T) circle (1.4pt) node[above right] {$T=(D_d,0)$};
  \fill (C) circle (1.4pt) node[below] {$(D_d/2,\,-\ell)$};
\end{tikzpicture}
\end{center}

\noindent\emph{The light ray as the upper arc of a circle of radius $kR_\oplus$ through $O$ and $T$, centred a distance $\ell$ below the chord.}

The light arc is a circle of radius $k R_\oplus$ passing through the observer and target. Its centre sits a distance $\ell = \sqrt{(k R_\oplus)^2 - (D_d/2)^2}$ below the midpoint of the chord, so the circle is

$$(k R_\oplus)^2 = \left(x - \frac{D_d}{2}\right)^2 + (y + \ell)^2 , \qquad \ell = \sqrt{(k R_\oplus)^2 - \left(\frac{D_d}{2}\right)^2}.$$

Expanding and simplifying:

$$(k R_\oplus)^2 = x^2 - D_d x + \left(\frac{D_d}{2}\right)^2 + y^2 + 2\ell y + (k R_\oplus)^2 - \left(\frac{D_d}{2}\right)^2$$
$$0 = y^2 + 2\ell y + x(x - D_d)$$

Solving the quadratic for $y$ (taking the upper arc):

$$y = \frac{-2\ell + \sqrt{(2\ell)^2 - 4x(x - D_d)}}{2} = \sqrt{\ell^2 - x(x - D_d)} - \ell$$

In `commons.py` this is written with $\gamma = \ell^2 = (k R_\oplus)^2 - (D_d/2)^2$:

$$y(x) = \sqrt{\gamma + x(D_d - x)} - \sqrt{\gamma}.$$
