# APPROACH_AND_METHODS.md — Hydrodynamic Modeling, Mathematical Formulations & Forecasting Engine

> **Project:** Bangkok & Central Thailand Flood Intelligence & Hydrodynamic Forecasting Platform (2026)  
> **Companion Documents:** `KNOWLEDGE.md`, `KNOWN_ISSUES.md`, `GUIDELINES.md`  
> **Audience:** Hydroinformatics Engineers, Machine Learning Researchers, and Software Developers  
> **Last Updated:** 26 September 2026

---

## 1. Executive Modeling Architecture: The 4 Hydraulic Regimes

Because Bangkok and the Central Plains span from mountain-fed rivers to an urbanized coastal delta, no single homogeneous equation can model the entire region. The engine partitions the watershed into four distinct physical regimes:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           REGIME A: UPSTREAM FLUVIAL REACH                      │
│   C.2 (Nakhon Sawan) ──► C.13 (Chao Phraya Dam) ──► C.35 (Ayutthaya) ──► C.29   │
│   Drivers: Dam releases, tributary inflows, catchment routing (Lag: 1-4 days)    │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Discharge Inflow Q_C29
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      REGIME B: TIDAL LOWER CHAO PHRAYA MAINSTEM                 │
│   Bang Sai (km 112) ──► Memorial Bridge (km 48) ──► Fort Chula (km 0)           │
│   Drivers: Fluvial flow + Astronomical tide + Wind surge (Lag: 8-24 hours)      │
└───────────────────────┬─────────────────────────────────┬───────────────────────┘
                        │ Backwater blocks gravity gates  │ Overtopping risk
                        ▼                                 ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│     REGIME C: URBAN KHLONGS & POLDERS │ │   REGIME D: STREET INUNDATION & ETA   │
│   Khlong Saen Saep, Lat Phrao, BMA    │ │   Doorstep depth d_street (cm)        │
│   Drivers: Local convective rain,     │ │   Recovery countdown clock T_dry      │
│   giant tunnels, pump capacity        │ │   Drivers: Road DEM, micro-ponding,   │
└───────────────────────────────────────┘ │   mechanical pump drawdown            │
                                          └───────────────────────────────────────┘
```

---

## 2. Multi-Tiered Model Ladder

To ensure reliability, models are developed and benchmarked according to a hierarchical ladder. Higher levels are only exposed if they statistically outperform lower levels in walk-forward backtesting:

| Level | Model Type | Mathematical Formulation | Primary Purpose |
| :--- | :--- | :--- | :--- |
| **L0** | **Persistence Baseline** | $H(t+h) = H(t)$ | Mandatory reference baseline |
| **L1** | **Persistence + Tide** | $H(t+h) = H(t) + \eta(t+h) - \eta(t)$ | Mandatory baseline for Regime B |
| **L2** | **Seasonal Climatology** | $H(t+h) = \text{Median}(H_{\text{day\_of\_year}})$ | Reference for long-range (+7d) outlooks |
| **L3** | **Physical Hydrodynamics** | Kinematic/Diffusion routing + Harmonic tides + Polder continuity | Interpretable, physically bounded core |
| **L4** | **ML Residual Model** | LightGBM Quantile Regression on physical residuals: $\Delta H_h$ | Non-linear feature learning across stations |
| **L5** | **Calibrated Ensemble** | LightGBM + AR(1) bias fading + NWP ensembles + Conformalized CQR | Operational probabilistic production model |
| **L6** | **Deep Sequence Models** | Temporal Fusion Transformers (TFT) / LSTMs | Advanced research upgrade path |
| **L7** | **1D/2D Hydrodynamic Solvers** | De Saint-Venant equations (HEC-RAS / MIKE 11 unsteady) | Offline floodway and levee breach modeling |

---

## 3. Mathematical Formulations by Regime

### 3.1 Regime A: Upstream Fluvial Routing

#### 1. Dynamic Wave Celerity Formulation
Flood waves propagate through the low-gradient alluvial channel ($S_0 \approx 1:50,000$) with a non-linear wave speed dependent on discharge:

$$c_k(Q) = c_0 \cdot \left( \frac{Q_{\text{upstream}}}{Q_{\text{bankfull}}} \right)^{0.38}$$

Where:
* $c_0 \approx 0.95 - 1.25\text{ m/s}$ ($3.4 - 4.5\text{ km/h}$) baseline channel celerity.
* $Q_{\text{bankfull}} \approx 2,500 - 3,000\text{ m}^3/\text{s}$ at Nakhon Sawan / Chai Nat.
* Travel delay from upstream station $A$ to downstream station $B$:
  $$\tau_f = \frac{x_A - x_B}{c_k(Q_A)}$$

#### 2. Muskingum Routing Balance
For in-channel wave smoothing between gauges:

$$O_{t+1} = C_0 I_{t+1} + C_1 I_t + C_2 O_t$$

Where coefficients are parameterized by storage time constant $K$ and weighting factor $x \in [0, 0.5]$:

$$C_0 = \frac{\Delta t - 2Kx}{2K(1-x) + \Delta t}, \quad C_1 = \frac{\Delta t + 2Kx}{2K(1-x) + \Delta t}, \quad C_2 = \frac{2K(1-x) - \Delta t}{2K(1-x) + \Delta t}$$

---

### 3.2 Regime B: Tidal Lower Chao Phraya Superposition

The water surface elevation along the tidal mainstem ($H_{\text{river}}$) combines fluvial discharge, astronomical tides, and meteorological storm surges:

$$H_{\text{river}}(x, t) = H_{\text{fluvial}}(x, t) + H_{\text{tide\_estuary}}(x, t)$$

#### 1. Astronomical Tide Harmonics (Seaward Boundary at Fort Chulachomklao)
$$H_{\text{ast}}(t) = Z_0(t) + \sum_{k=1}^{M} f_k A_k \cos\left( \omega_k t + (V_k + u_k) - \kappa_k \right)$$

Key constituents in the Gulf of Thailand:
* $M_2$ (Principal lunar semi-diurnal, $\omega = 28.984^\circ/\text{hr}$)
* $S_2$ (Principal solar semi-diurnal, $\omega = 30.000^\circ/\text{hr}$)
* $K_1$ (Soli-lunar diurnal, $\omega = 15.041^\circ/\text{hr}$)
* $O_1$ (Principal lunar diurnal, $\omega = 13.943^\circ/\text{hr}$)
* $Z_0(t)$ (Seasonal monsoonal sea-level anomaly: $+0.30\text{ to }+0.55\text{ m MSL}$ in Oct–Dec).

#### 2. Estuarine Tidal Propagation & Frictional Damping
As the tidal wave ascends the river mouth ($x = 0$) toward upstream chainage $x$:

$$H_{\text{tide\_estuary}}(x, t) = H_{\text{sea}}(t - \tau_t(x)) \cdot \exp\left(-\mu_{\text{tide}}(Q) \cdot x\right)$$

Where:
* Upstream phase lag: $\tau_t(x) \approx 0.058\text{ hr/km}$ (~35 minutes per 10 km).
* Discharge damping coefficient:
  $$\mu_{\text{tide}}(Q) = \mu_0 + \kappa_Q \left( \frac{Q_{\text{C29}}}{Q_{\text{bankfull}}} \right)^{1.5}$$
  High river discharges extinguish tidal oscillation in the upper river while inducing strong backwater stacking between Bang Na and Memorial Bridge.

---

### 3.3 Regime C: Urban Khlong & Polder Inundation

Bangkok polders operate as hydrological reservoirs with mechanical and gravity evacuation:

$$A_{\text{water}} \frac{dH_{\text{canal}}}{dt} = Q_{\text{runoff}}(t) + Q_{\text{lateral}}(t) - Q_{\text{pump\_out}}(t) - Q_{\text{gravity\_out}}(t)$$

#### 1. Rain-to-Runoff Generation (Modified Rational Method)
$$Q_{\text{runoff}}(t) = C_{\text{composite}} \cdot I_{\text{eff}}(t) \cdot A_{\text{polder}}$$

Where:
* $C_{\text{composite}} \approx 0.85 - 0.92$ (dense concrete urban surface).
* $I_{\text{eff}}(t) = \max\left(0, P(t) - f_{\text{loss}}\right)$ is effective precipitation.

#### 2. Sluice Gate Gravity Hydraulics
Gravity discharge through river sluice gates operates strictly when the canal elevation exceeds the river:

$$Q_{\text{gravity\_out}} = \begin{cases} 
C_d B_{\text{gate}} Y_{\text{open}} \sqrt{2g \left( H_{\text{canal}} - H_{\text{river}} \right)} & \text{if } H_{\text{canal}} > H_{\text{river}} \\ 
0 & \text{if } H_{\text{canal}} \le H_{\text{river}} \text{ (Flap gates sealed)} 
\end{cases}$$

#### 3. Mechanical Pumping Discharge
$$Q_{\text{pump\_out}}(t) = \eta_{\text{efficiency}} \cdot \sum Q_{\text{active\_pumps}}$$
*(where $\eta_{\text{efficiency}} \approx 0.75 - 0.85$ accounting for debris screen friction)*.

---

### 3.4 Regime D: Street Inundation Depth & Recovery Time ($T_{\text{dry}}$)

#### 1. Local Street Inundation Depth ($d_{\text{street}}$)
$$d_{\text{street}}(x, y, t) = \max\left(0, \, H_{\text{canal}}(t) - Z_{\text{road}}(x, y)\right) + \Delta h_{\text{cloudburst\_ponding}}(P)$$

Where:
* $Z_{\text{road}}(x, y)$ is road surface elevation (m MSL) from FABDEM / calibrated LiDAR.
* $\Delta h_{\text{cloudburst\_ponding}} = \frac{\max(0, P_{\text{1h}} - 60\text{ mm})}{1000} \times \gamma_{\text{gutter}}$ models immediate curb overflow when rainfall intensity surpasses subterranean pipe capacity ($60\text{ mm/hr}$).

#### 2. Analytical Time-to-Dry Recovery Model ($T_{\text{dry}}$)
The recovery duration represents the time required to evacuate the ponded volume over a road depression back to $d_{\text{street}} = 0$:

$$T_{\text{dry}} = \frac{V_{\text{ponding}}(t_0)}{Q_{\text{net\_evacuation}}} = \frac{d_{\text{street}}(t_0) \cdot A_{\text{basin}} \cdot \gamma_{\text{surface}}}{\left[ \sum Q_{\text{pump}} \cdot \left(\frac{A_{\text{basin}}}{A_{\text{polder}}}\right) \right] + Q_{\text{gravity}} - Q_{\text{residual\_rain}}}$$

The model converts $T_{\text{dry}}$ into a human-readable local timestamp:
$$T_{\text{recovery\_clock}} = t_{\text{current}} + T_{\text{dry}} \quad \longrightarrow \quad \text{"18:45 น. (26 ก.ย.)"}$$

---

## 4. Machine Learning Residual Engine (LightGBM)

Rather than predicting absolute stage directly, the ML model predicts the **change in level ($\Delta H_h$)** or the **residual of the physical baseline**:

$$H(t+h) = H_{\text{physical\_baseline}}(t+h) + \hat{r}(t+h)$$

### 4.1 Loss Function & Quantiles
LightGBM is trained with pinball quantile loss across 5 quantiles to produce the forecast fan chart:
$$\tau \in \{0.05, 0.25, 0.50, 0.75, 0.95\}$$

$$\mathcal{L}_{\tau}(y, \hat{y}) = \max\left( \tau (y - \hat{y}), \, (1 - \tau)(\hat{y} - y) \right)$$

### 4.2 Feature Matrix
1. **Dynamic Inputs:**
   * Past stage and slope: $H(t), \frac{dH}{dt}_{1\text{h}}, \frac{dH}{dt}_{3\text{h}}, \frac{dH}{dt}_{24\text{h}}$.
   * Upstream discharge: $Q_{\text{C29}}(t - \tau_f)$.
   * Seaward tidal state: $H_{\text{ast}}(t+h)$, daily tidal high water $\max(\eta)$.
   * Weather forcing: Observed rain accumulations ($1, 3, 6, 24\text{h}$) + NWP forecasted rain ($+12\text{h}, +24\text{h}, +48\text{h}$).
   * Interaction terms: $Q_{\text{C29}} \times \max(H_{\text{ast}})$.
2. **Static Embeddings:**
   * Station distance to river mouth ($x_{\text{km}}$).
   * Bank level elevation ($H_{\text{bank}}$).
   * Polder pump capacity ($Q_{\text{pump\_max}}$).
3. **Monotonic Physics Constraints:**
   * $\frac{\partial \hat{H}}{\partial Q_{\text{upstream}}} \ge 0$ (Increased upstream discharge cannot lower water level).
   * $\frac{\partial \hat{H}}{\partial P_{\text{rain}}} \ge 0$ (Increased rainfall cannot lower water level).

---

## 5. Post-Processing & Uncertainty Calibration

### 5.1 Autoregressive Residual Correction (AR-1)
To eliminate systematic real-time bias while preserving long-term stability:

$$\hat{\varepsilon}(t+h) = \phi^h \cdot \left[ H_{\text{observed}}(t) - H_{\text{model}}(t) \right]$$

Where autoregressive parameter $\phi \in [0.85, 0.95]$ smoothly dampens error correction to zero as the horizon $h$ extends.

### 5.2 Conformalized Quantile Regression (CQR)
To guarantee that user-facing intervals reflect real-world coverage:
1. Compute non-conformity scores on calibration events:
   $$E_i = \max\left( \hat{q}_{\text{low}}(x_i) - y_i, \, y_i - \hat{q}_{\text{high}}(x_i) \right)$$
2. Determine $(1 - \alpha)$ empirical quantile $Q_{1-\alpha}(E)$.
3. Calibrated prediction interval:
   $$C(x) = \left[ \hat{q}_{\text{low}}(x) - Q_{1-\alpha}(E), \; \hat{q}_{\text{high}}(x) + Q_{1-\alpha}(E) \right]$$
4. Track empirical coverage daily; if coverage on the 90% band dips below 85%, dynamically inflate calibration intervals via **Adaptive Conformal Inference (ACI)**.
