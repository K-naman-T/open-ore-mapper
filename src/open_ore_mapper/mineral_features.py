from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiagnosticFeature:
    position_nm: float
    depth_min: float
    depth_max: float
    fwhm_nm: float
    asymmetry: float
    assignment: str
    notes: str = ""


@dataclass(frozen=True)
class MineralExpertProfile:
    name: str
    group: str
    alteration: str
    features: list[DiagnosticFeature]
    aliases: list[str] = field(default_factory=list)
    discrimination: str = ""
    notes: str = ""


MINERAL_FEATURES: list[MineralExpertProfile] = [
    # ── Iron Oxides (VNIR) ──────────────────────────────────────────────
    MineralExpertProfile(
        name="hematite",
        group="iron_oxide",
        alteration="gossan",
        features=[
            DiagnosticFeature(530.0, 0.05, 0.40, 60.0, 0.9, "Fe3+ crystal field", "primary: broad asymmetric feature"),
            DiagnosticFeature(650.0, 0.02, 0.15, 40.0, 1.2, "Fe3+ shoulder", "diagnostic shoulder on 860nm band"),
            DiagnosticFeature(860.0, 0.10, 0.55, 100.0, 0.8, "Fe3+ crystal field", "primary diagnostic feature; narrower than goethite"),
        ],
        discrimination="860nm vs goethite 930nm; 650nm shoulder stronger than goethite",
        notes="Red ochre. Distinguish from goethite by 860nm vs 930nm position. Hematite has sharper ~100nm FWHM at 860nm vs goethite ~140nm.",
    ),
    MineralExpertProfile(
        name="goethite",
        group="iron_oxide",
        alteration="gossan",
        features=[
            DiagnosticFeature(500.0, 0.05, 0.35, 70.0, 1.0, "Fe3+ crystal field", "broader than hematite 530nm"),
            DiagnosticFeature(650.0, 0.01, 0.10, 50.0, 1.1, "Fe3+ shoulder", "weaker shoulder than hematite"),
            DiagnosticFeature(930.0, 0.10, 0.50, 140.0, 0.7, "Fe3+ crystal field", "broader than hematite 860nm; key discriminant"),
        ],
        discrimination="930nm primary vs hematite 860nm; broader FWHM ~140nm",
        notes="Yellow-brown ochre. Primary iron hydroxide in gossans. Position at 930nm vs 860nm is the key discriminant from hematite.",
    ),
    MineralExpertProfile(
        name="jarosite",
        group="sulfate",
        alteration="gossan_amd",
        features=[
            DiagnosticFeature(430.0, 0.05, 0.30, 50.0, 1.1, "Fe3+ crystal field", "sharp feature in visible"),
            DiagnosticFeature(920.0, 0.08, 0.45, 120.0, 0.9, "Fe3+ crystal field", "broad, near goethite position"),
            DiagnosticFeature(1470.0, 0.02, 0.10, 40.0, 1.0, "OH overtone", "weak feature"),
            DiagnosticFeature(1850.0, 0.02, 0.08, 35.0, 1.0, "H2O combination", "weak water feature"),
            DiagnosticFeature(2260.0, 0.10, 0.60, 70.0, 1.2, "OH-Fe stretch", "UNIQUE: only mineral with both 920nm Fe + 2260nm OH-Fe"),
        ],
        discrimination="2260nm OH-Fe feature is unique among iron minerals; distinguishes from hematite/goethite which lack OH",
        notes="KFe3(SO4)2(OH)6. Key AMD indicator. The 2260nm OH-Fe feature is diagnostic and present in no other common iron oxide.",
    ),
    MineralExpertProfile(
        name="magnetite",
        group="iron_oxide",
        alteration="primary",
        features=[],  # featureless opaque; low albedo
        notes="Fe3O4. Opaque mineral. Featureless in VNIR-SWIR. Low uniform albedo. Presence inferred from dark pixels with no absorption features.",
    ),
    MineralExpertProfile(
        name="ferrihydrite",
        group="iron_oxide",
        alteration="gossan",
        features=[
            DiagnosticFeature(550.0, 0.05, 0.25, 80.0, 1.0, "Fe3+ crystal field", "broad"),
            DiagnosticFeature(720.0, 0.03, 0.15, 120.0, 0.9, "Fe3+ broad band", "broad, poorly crystallized"),
        ],
        notes="Fe5HO8·4H2O. Poorly crystalline. Broad, weak features. Often associated with acid mine drainage.",
    ),
    MineralExpertProfile(
        name="limonite",
        group="iron_oxide",
        alteration="gossan",
        features=[
            DiagnosticFeature(500.0, 0.05, 0.25, 80.0, 1.0, "Fe3+ crystal field", "broad composite"),
            DiagnosticFeature(940.0, 0.05, 0.35, 150.0, 0.8, "Fe3+ crystal field", "very broad; mixture of hematite+goethite"),
        ],
        notes="Generic term for Fe-oxide/hydroxide mixture. Broad composite features. Not a true mineral species.",
    ),
    # ── Phyllosilicates: Kaolin Group ───────────────────────────────────
    MineralExpertProfile(
        name="kaolinite",
        group="phyllosilicate",
        alteration="argillic",
        features=[
            DiagnosticFeature(1400.0, 0.05, 0.30, 40.0, 1.0, "OH stretch", "doublet; key cluster"),
            DiagnosticFeature(2160.0, 0.02, 0.15, 25.0, 0.7, "Al-OH shoulder", "DIAGNOSTIC: shoulder at 2160nm distinguishes from dickite"),
            DiagnosticFeature(2200.0, 0.15, 0.70, 50.0, 1.3, "Al-OH combination", "primary diagnostic feature; asymmetric with shoulder"),
            DiagnosticFeature(2320.0, 0.02, 0.10, 30.0, 1.0, "Al-OH", "secondary"),
            DiagnosticFeature(2380.0, 0.02, 0.10, 35.0, 1.0, "OH combination", "secondary"),
        ],
        aliases=["kaolin"],
        discrimination="2160nm shoulder presence vs dickite (no shoulder); doublet at 1400nm",
        notes="Al2Si2O5(OH)4. KEY clay for argillic alteration. The 2160nm shoulder on the 2200nm feature is the primary discriminant from dickite. The 1400nm region shows a clear doublet.",
    ),
    MineralExpertProfile(
        name="dickite",
        group="phyllosilicate",
        alteration="argillic",
        features=[
            DiagnosticFeature(2200.0, 0.15, 0.65, 45.0, 1.1, "Al-OH combination", "symmetric; NO 2160nm shoulder"),
            DiagnosticFeature(2320.0, 0.02, 0.10, 30.0, 1.0, "Al-OH", "secondary"),
        ],
        discrimination="NO 2160nm shoulder; symmetric 2200nm vs kaolinite asymmetric with shoulder",
        notes="Al2Si2O5(OH)4. Polymorph of kaolinite. Distinguished by ABSENCE of 2160nm shoulder and more symmetric 2200nm feature.",
    ),
    # ── Phyllosilicates: Mica / Illite Group ────────────────────────────
    MineralExpertProfile(
        name="illite",
        group="phyllosilicate",
        alteration="phyllic_sericitic",
        features=[
            DiagnosticFeature(1900.0, 0.02, 0.10, 50.0, 1.0, "H2O combination", "weak to moderate water band"),
            DiagnosticFeature(2200.0, 0.10, 0.50, 60.0, 0.8, "Al-OH combination", "moderately asymmetric; less than montmorillonite"),
            DiagnosticFeature(2340.0, 0.05, 0.25, 40.0, 1.0, "Al-OH/Fe-OH", "secondary"),
            DiagnosticFeature(2440.0, 0.02, 0.10, 30.0, 1.0, "Al-OH", "weak secondary"),
        ],
        aliases=["illite_clay"],
        discrimination="1900nm water band weaker than montmorillonite; 2200nm less broad than smectite; 2340nm present",
        notes="K-clay mica. Common in phyllic/ sericitic alteration. Moderate water at 1900nm distinguishes from muscovite (weaker water). 2200nm less asymmetric than montmorillonite.",
    ),
    MineralExpertProfile(
        name="muscovite",
        group="phyllosilicate",
        alteration="phyllic_sericitic",
        features=[
            DiagnosticFeature(1900.0, 0.01, 0.05, 40.0, 1.0, "H2O combination", "very weak or absent"),
            DiagnosticFeature(2200.0, 0.15, 0.60, 45.0, 1.1, "Al-OH combination", "sharp, narrow; more symmetric than illite"),
            DiagnosticFeature(2340.0, 0.05, 0.25, 35.0, 1.0, "Al-OH", "secondary"),
            DiagnosticFeature(2440.0, 0.03, 0.12, 30.0, 1.0, "Al-OH", "secondary"),
        ],
        aliases=["white_mica", "sericite"],
        discrimination="Sharper 2200nm than illite; weaker 1900nm water; higher albedo than illite",
        notes="KAl2(AlSi3O10)(F,OH)2. 'Sericite' in phyllic alteration. Distinguished from illite by sharper 2200nm and weaker 1900nm water. Higher reflectance than illite.",
    ),
    # ── Phyllosilicates: Smectite Group ─────────────────────────────────
    MineralExpertProfile(
        name="montmorillonite",
        group="phyllosilicate",
        alteration="argillic",
        features=[
            DiagnosticFeature(1400.0, 0.05, 0.25, 60.0, 1.0, "OH stretch", "broad"),
            DiagnosticFeature(1900.0, 0.10, 0.50, 80.0, 1.0, "H2O combination", "STRONG water band; key feature"),
            DiagnosticFeature(2200.0, 0.10, 0.50, 70.0, 0.7, "Al-OH combination", "broad and asymmetric; less depth than kaolinite"),
            DiagnosticFeature(2340.0, 0.02, 0.10, 40.0, 1.0, "Al-OH", "weak secondary"),
        ],
        aliases=["smectite"],
        discrimination="STRONG 1900nm water band; broad asymmetric 2200nm; no 2160nm shoulder (vs kaolinite)",
        notes="Na,Ca-smectite. Strong 1900nm water distinguishes from illite and kaolinite. Broad 2200nm feature is diagnostic of expandable clays.",
    ),
    MineralExpertProfile(
        name="nontronite",
        group="phyllosilicate",
        alteration="argillic",
        features=[
            DiagnosticFeature(1900.0, 0.08, 0.40, 80.0, 1.0, "H2O combination", "strong water band"),
            DiagnosticFeature(2250.0, 0.10, 0.45, 70.0, 0.8, "Fe-OH combination", "DIAGNOSTIC: Fe-OH at 2250nm instead of Al-OH at 2200nm"),
            DiagnosticFeature(2340.0, 0.05, 0.20, 45.0, 1.0, "Mg-OH", "secondary"),
        ],
        aliases=["Fe-smectite"],
        discrimination="2250nm Fe-OH vs montmorillonite 2200nm Al-OH; strong 1900nm water",
        notes="Fe-rich smectite. The Fe-OH feature at 2250nm (vs 2200nm for Al-OH) is diagnostic. Associated with Fe-rich alteration environments.",
    ),
    # ── Phyllosilicates: Chlorite Group ──────────────────────────────────
    MineralExpertProfile(
        name="chlorite",
        group="phyllosilicate",
        alteration="propylitic",
        features=[
            DiagnosticFeature(2250.0, 0.05, 0.30, 50.0, 1.0, "Fe-OH combination", "DIAGNOSTIC: Fe-OH feature"),
            DiagnosticFeature(2330.0, 0.08, 0.40, 55.0, 1.0, "Mg-OH combination", "DIAGNOSTIC: Mg-OH doublet with Fe-OH; intensity varies with Fe/Mg ratio"),
            DiagnosticFeature(2380.0, 0.02, 0.10, 35.0, 1.0, "OH combination", "secondary"),
        ],
        aliases=["chlorite_group"],
        discrimination="2250+2330nm doublet is diagnostic; Fe/Mg ratio shifts relative depths",
        notes="(Mg,Fe)5Al(AlSi3O10)(OH)8. KEY propylitic alteration mineral. Fe-OH at 2250nm + Mg-OH at 2330nm form diagnostic doublet. Ratio of depths gives Fe/Mg composition.",
    ),
    MineralExpertProfile(
        name="biotite",
        group="phyllosilicate",
        alteration="potassic",
        features=[
            DiagnosticFeature(2250.0, 0.03, 0.15, 45.0, 1.0, "Fe-OH", "weak to moderate"),
            DiagnosticFeature(2330.0, 0.10, 0.45, 50.0, 1.0, "Mg-OH combination", "DIAGNOSTIC: strong Mg-OH"),
        ],
        discrimination="2330nm strong vs muscovite 2200nm; Fe-OH at 2250nm weaker than chlorite",
        notes="K(Mg,Fe)3AlSi3O10(F,OH)2. KEY mineral in potassic alteration. Primary Mg-OH at 2330nm. Distinguished from chlorite by weaker Fe-OH at 2250nm.",
    ),
    # ── Phyllosilicates: Other ──────────────────────────────────────────
    MineralExpertProfile(
        name="pyrophyllite",
        group="phyllosilicate",
        alteration="advanced_argillic",
        features=[
            DiagnosticFeature(2080.0, 0.02, 0.10, 30.0, 1.0, "Al-OH", "pre-2200nm feature; uncommon"),
            DiagnosticFeature(2160.0, 0.02, 0.10, 25.0, 1.0, "Al-OH", "secondary"),
            DiagnosticFeature(2200.0, 0.15, 0.60, 45.0, 1.1, "Al-OH combination", "sharp, symmetric; deeper than kaolinite"),
            DiagnosticFeature(2320.0, 0.05, 0.20, 35.0, 1.0, "Al-OH", "secondary"),
        ],
        discrimination="2080nm feature is diagnostic for pyrophyllite; sharp 2200nm; associated with advanced argillic",
        notes="Al2Si4O10(OH)2. Key mineral in advanced argillic alteration (epithermal Au). 2080nm feature is diagnostic. Sharp symmetric 2200nm is deeper than kaolinite.",
    ),
    MineralExpertProfile(
        name="talc",
        group="phyllosilicate",
        alteration="magnesium",
        features=[
            DiagnosticFeature(2310.0, 0.10, 0.50, 35.0, 1.1, "Mg-OH combination", "very narrow, symmetric; DIAGNOSTIC"),
            DiagnosticFeature(2380.0, 0.02, 0.10, 30.0, 1.0, "OH", "secondary"),
        ],
        notes="Mg3Si4O10(OH)2. Very narrow Mg-OH at 2310nm (~35nm FWHM). Distinguished from other Mg-OH minerals by narrowness and position.",
    ),
    # ── Carbonates ──────────────────────────────────────────────────────
    MineralExpertProfile(
        name="calcite",
        group="carbonate",
        alteration="propylitic",
        features=[
            DiagnosticFeature(1870.0, 0.02, 0.10, 40.0, 1.0, "CO3 overtone", "weak"),
            DiagnosticFeature(2000.0, 0.02, 0.08, 35.0, 1.0, "CO3 combination", "weak"),
            DiagnosticFeature(2160.0, 0.02, 0.10, 30.0, 1.0, "CO3 combination", "moderate"),
            DiagnosticFeature(2340.0, 0.10, 0.60, 50.0, 1.0, "CO3 overtone", "PRIMARY diagnostic: 2340nm is key for calcite"),
            DiagnosticFeature(2500.0, 0.05, 0.30, 45.0, 1.0, "CO3 overtone", "edge of SWIR range"),
        ],
        discrimination="2340nm feature vs dolomite 2320nm; ~20nm shift is resolvable at 7.5nm sampling",
        notes="CaCO3. Key propylitic alteration carbonate. Primary CO3 absorption at 2340nm. Shift from dolomite is ~20nm. With 7.5nm EMIT sampling, this is resolvable (~2.6× FWHM separation) via continuum removal and sub-pixel fitting.",
    ),
    MineralExpertProfile(
        name="dolomite",
        group="carbonate",
        alteration="propylitic",
        features=[
            DiagnosticFeature(2320.0, 0.10, 0.55, 50.0, 1.0, "CO3 overtone", "PRIMARY: blue-shifted from calcite"),
            DiagnosticFeature(2250.0, 0.02, 0.08, 30.0, 1.0, "CO3/Mg-OH", "weak secondary"),
            DiagnosticFeature(2480.0, 0.05, 0.25, 45.0, 1.0, "CO3", "edge of SWIR"),
        ],
        discrimination="2320nm vs calcite 2340nm; Mg content causes blue shift",
        notes="CaMg(CO3)2. Mg substitution shifts primary absorption from 2340nm (calcite) to 2320nm. This ~20nm shift is the key discriminator.",
    ),
    MineralExpertProfile(
        name="magnesite",
        group="carbonate",
        alteration="magnesium",
        features=[
            DiagnosticFeature(2300.0, 0.10, 0.50, 45.0, 1.0, "CO3 overtone", "PRIMARY: further blue-shifted"),
            DiagnosticFeature(2250.0, 0.02, 0.08, 28.0, 1.0, "CO3/Mg-OH", "secondary"),
        ],
        notes="MgCO3. Further blue shift from dolomite. 2300nm primary. Associated with ultramafic alteration.",
    ),
    MineralExpertProfile(
        name="siderite",
        group="carbonate",
        alteration="coal_measure",
        features=[
            DiagnosticFeature(1200.0, 0.02, 0.10, 100.0, 0.8, "Fe2+ crystal field", "broad Fe feature"),
            DiagnosticFeature(2300.0, 0.05, 0.30, 60.0, 0.9, "CO3 overtone", "broadened by Fe substitution; shifted from calcite"),
        ],
        discrimination="2300nm CO3 + broad 1200nm Fe2+ feature; distinguishes from other carbonates",
        notes="FeCO3. Common in coal measures (Dhanbad, Jharia). Fe2+ broadens the CO3 feature and adds a broad 1200nm absorption. Distinguish from calcite/dolomite by 2300nm position and Fe feature.",
    ),
    MineralExpertProfile(
        name="ankerite",
        group="carbonate",
        alteration="hydrothermal",
        features=[
            DiagnosticFeature(2325.0, 0.08, 0.40, 55.0, 0.9, "CO3 overtone", "intermediate between calcite and dolomite"),
            DiagnosticFeature(1100.0, 0.02, 0.08, 80.0, 0.9, "Fe2+", "broad Fe feature from Fe substitution"),
        ],
        notes="Ca(Fe,Mg)(CO3)2. Fe-bearing dolomite group. CO3 absorption at ~2325nm. Broad Fe2+ feature in NIR from Fe substitution.",
    ),
    # ── Sulfates ────────────────────────────────────────────────────────
    MineralExpertProfile(
        name="alunite",
        group="sulfate",
        alteration="advanced_argillic",
        features=[
            DiagnosticFeature(1480.0, 0.02, 0.10, 35.0, 1.0, "OH overtone", "weak"),
            DiagnosticFeature(1760.0, 0.02, 0.08, 30.0, 1.0, "SO4 overtone", "weak"),
            DiagnosticFeature(2170.0, 0.10, 0.50, 35.0, 1.1, "Al-OH combination", "DIAGNOSTIC: distinct from kaolinite"),
            DiagnosticFeature(2220.0, 0.05, 0.30, 30.0, 0.8, "Al-OH", "DIAGNOSTIC: shoulder/peak forming doublet with 2170nm"),
            DiagnosticFeature(2320.0, 0.03, 0.15, 35.0, 1.0, "Al-OH", "secondary"),
        ],
        aliases=["alunite_group"],
        discrimination="2170+2220nm doublet is diagnostic for alunite; distinguishes from kaolinite (2200nm single primary)",
        notes="KAl3(SO4)2(OH)6. KEY advanced argillic alteration mineral. The 2170+2220nm doublet is diagnostic. Often associated with epithermal Au systems.",
    ),
    MineralExpertProfile(
        name="gypsum",
        group="sulfate",
        alteration="evaporite_amd",
        features=[
            DiagnosticFeature(1440.0, 0.05, 0.30, 30.0, 1.0, "H2O combination", "sharp"),
            DiagnosticFeature(1490.0, 0.05, 0.25, 25.0, 1.0, "H2O combination", "triplet component"),
            DiagnosticFeature(1530.0, 0.03, 0.15, 25.0, 1.0, "H2O combination", "triplet component"),
            DiagnosticFeature(1740.0, 0.02, 0.10, 30.0, 1.0, "H2O combination", "weak"),
            DiagnosticFeature(1900.0, 0.15, 0.60, 70.0, 1.0, "H2O combination", "VERY STRONG water; diagnostic"),
            DiagnosticFeature(2210.0, 0.02, 0.10, 40.0, 1.0, "OH/H2O", "weak"),
        ],
        aliases=["gypsum_caso4"],
        discrimination="Strong 1900nm + triplet at 1440-1530nm is unique to gypsum among common minerals",
        notes="CaSO4·2H2O. Strong water features throughout SWIR. The 1440-1530nm triplet + strong 1900nm are diagnostic. Common in AMD environments and evaporites.",
    ),
    # ── Silicates: Framework (Tectosilicates) ───────────────────────────
    MineralExpertProfile(
        name="quartz",
        group="tectosilicate",
        alteration="silicification",
        features=[],  # featureless in VNIR-SWIR
        notes="SiO2. No diagnostic absorption features in VNIR-SWIR. Featureless, high albedo. Presence inferred from bright pixels with no features.",
    ),
    MineralExpertProfile(
        name="k_feldspar",
        group="tectosilicate",
        alteration="potassic",
        features=[
            DiagnosticFeature(2200.0, 0.01, 0.05, 40.0, 1.0, "Al-OH impurity", "very weak; from clay impurities"),
            DiagnosticFeature(1900.0, 0.01, 0.03, 50.0, 1.0, "H2O impurity", "very weak"),
        ],
        aliases=["orthoclase", "microcline"],
        notes="KAlSi3O8. Very weak or no diagnostic features in VNIR-SWIR. Usually featureless. The presence in potassic alteration is inferred from bright pixels lacking mica/chlorite features.",
    ),
    MineralExpertProfile(
        name="plagioclase",
        group="tectosilicate",
        alteration="propylitic",
        features=[
            DiagnosticFeature(1100.0, 0.01, 0.05, 80.0, 1.0, "Fe2+ impurity", "very weak broad Fe"),
        ],
        aliases=["albite", "oligoclase", "andesine", "labradorite"],
        notes="(Na,Ca)(Al,Si)4O8. Weak or no diagnostic VNIR-SWIR features. Slight Fe2+ absorption in NIR from trace Fe. Generally featureless.",
    ),
    # ── Silicates: Sorosilicates ────────────────────────────────────────
    MineralExpertProfile(
        name="epidote",
        group="sorosilicate",
        alteration="propylitic",
        features=[
            DiagnosticFeature(2250.0, 0.05, 0.25, 45.0, 1.0, "Fe-OH", "moderate Fe-OH feature"),
            DiagnosticFeature(2340.0, 0.08, 0.35, 50.0, 1.0, "Al-OH/Fe-OH", "secondary; overlaps with calcite region"),
        ],
        aliases=["epidote_group"],
        discrimination="2250nm + 2340nm; Fe-OH presence distinguishes from pure calcite",
        notes="Ca2(Al,Fe)3(SiO4)3(OH). Common in propylitic alteration. Often found with chlorite and calcite. Fe-OH at 2250nm and broader feature near 2340nm.",
    ),
    MineralExpertProfile(
        name="tourmaline",
        group="cyclosilicate",
        alteration="greisen",
        features=[
            DiagnosticFeature(2200.0, 0.05, 0.30, 50.0, 1.0, "OH stretch", "variable position by composition"),
            DiagnosticFeature(2340.0, 0.03, 0.15, 40.0, 1.0, "OH", "secondary"),
        ],
        notes="Complex borosilicate. OH absorption near 2200nm but position varies with composition. Associated with greisen alteration.",
    ),
    # ── Amphiboles / Pyroxenes ─────────────────────────────────────────
    MineralExpertProfile(
        name="amphibole",
        group="inosilicate",
        alteration="skarn",
        features=[
            DiagnosticFeature(900.0, 0.02, 0.10, 100.0, 0.9, "Fe2+ crystal field", "broad Fe feature"),
            DiagnosticFeature(2300.0, 0.05, 0.25, 60.0, 1.0, "OH stretch", "broad OH from structural water"),
        ],
        notes="General amphibole group. Broad Fe2+ feature near 900nm. OH near 2300nm. Associated with skarn alteration.",
    ),
    # ── Coal and Coal-related ───────────────────────────────────────────
    MineralExpertProfile(
        name="coal",
        group="organic",
        alteration="coal_measure",
        features=[],  # featureless low albedo
        notes="Coal (bituminous/sub-bituminous). Uniformly low albedo in VNIR-SWIR. No diagnostic absorption features. Featureless dark pixels. Presence inferred from very low reflectance with no mineral absorption features.",
    ),
    MineralExpertProfile(
        name="pyrite",
        group="sulfide",
        alteration="phyllic_gossan",
        features=[],  # opaque, featureless
        aliases=["fool_gold", "iron_pyrite"],
        notes="FeS2. Opaque mineral. No diagnostic VNIR-SWIR absorption features. Low albedo. Often associated with phyllic alteration. Can oxidize to form gossan minerals.",
    ),
    # ── Thermally Altered Clays (Coal Fire) ────────────────────────────
    MineralExpertProfile(
        name="meta_kaolinite",
        group="phyllosilicate",
        alteration="coal_fire",
        features=[
            DiagnosticFeature(2180.0, 0.05, 0.30, 50.0, 1.0, "Al-OH", "shifted from 2200nm due to thermal dehydroxylation"),
            DiagnosticFeature(1900.0, 0.01, 0.05, 50.0, 1.0, "H2O", "very weak; water driven off"),
        ],
        discrimination="Shifted 2200nm absorption to shorter wavelength (~2180nm); weakened 1900nm water",
        notes="Kaolinite thermally altered by coal fires. Dehydroxylation shifts the 2200nm feature to shorter wavelengths (~2180nm). Water band at 1900nm weakens significantly. Key indicator of coal fire zones in Jharia/Dhanbad.",
    ),
    # ── Soil/Occasional ────────────────────────────────────────────────
    MineralExpertProfile(
        name="calcite_clay_mix",
        group="mixture",
        alteration="soil",
        features=[
            DiagnosticFeature(2200.0, 0.05, 0.30, 60.0, 1.0, "Al-OH", "clay component"),
            DiagnosticFeature(2340.0, 0.05, 0.25, 50.0, 1.0, "CO3", "carbonate component"),
            DiagnosticFeature(1900.0, 0.03, 0.20, 70.0, 1.0, "H2O", "variable water"),
        ],
        notes="Common soil mixture. Composite features from clay + carbonate. Not a true mineral but useful for background classification.",
    ),
    MineralExpertProfile(
        name="unclassified_low_albedo",
        group="unclassified",
        alteration="background",
        features=[],
        notes="Catch-all for featureless dark pixels: coal, magnetite, pyrite, shadow, water. Requires additional context for disambiguation.",
    ),
    MineralExpertProfile(
        name="unclassified_high_albedo",
        group="unclassified",
        alteration="background",
        features=[],
        notes="Catch-all for featureless bright pixels: quartz, k-feldspar, snow, clouds. Requires additional context for disambiguation.",
    ),
]


ALTERATION_ASSEMBLAGES: dict[str, dict[str, str | list[str]]] = {
    "porphyry_copper_phyllic": {
        "description": "Sericite + pyrite alteration; pervasive in porphyry Cu systems",
        "key_minerals": ["muscovite", "pyrite"],
        "diagnostic_features": "2200nm Al-OH from sericite; pyrite as dark featureless",
    },
    "porphyry_copper_potassic": {
        "description": "K-feldspar + biotite ± magnetite; inner zone of porphyry systems",
        "key_minerals": ["k_feldspar", "biotite"],
        "diagnostic_features": "2330nm Mg-OH from biotite; featureless K-feldspar bright matrix",
    },
    "porphyry_copper_argillic": {
        "description": "Kaolinite + montmorillonite ± illite; intermediate argillic zone",
        "key_minerals": ["kaolinite", "montmorillonite", "illite"],
        "diagnostic_features": "2200nm Al-OH clays; 1900nm water for smectite; 2160nm shoulder for kaolinite",
    },
    "porphyry_copper_propylitic": {
        "description": "Chlorite + epidote + calcite; distal alteration zone",
        "key_minerals": ["chlorite", "epidote", "calcite"],
        "diagnostic_features": "Chlorite 2250+2330nm doublet; Calcite 2340nm; Epidote 2250+2340nm",
    },
    "epithermal_gold_advanced_argillic": {
        "description": "Alunite + kaolinite + pyrophyllite ± dickite; high-sulfidation epithermal",
        "key_minerals": ["alunite", "kaolinite", "pyrophyllite", "dickite"],
        "diagnostic_features": "Alunite 2170+2220nm doublet; Pyrophyllite 2080nm; Kaolinite 2200nm with 2160nm shoulder",
    },
    "epithermal_gold_silicification": {
        "description": "Quartz ± chalcedony; silica cap",
        "key_minerals": ["quartz"],
        "diagnostic_features": "Featureless bright pixels",
    },
    "vms_chlorite_sericite": {
        "description": "Chlorite + sericite alteration; common in VMS hanging wall",
        "key_minerals": ["chlorite", "muscovite"],
        "diagnostic_features": "Chlorite 2250+2330nm doublet; Sericite 2200nm Al-OH",
    },
    "vms_gossan": {
        "description": "Hematite + goethite + jarosite; oxidized sulfide cap",
        "key_minerals": ["hematite", "goethite", "jarosite"],
        "diagnostic_features": "Hematite 860nm; Goethite 930nm; Jarosite 920+2260nm",
    },
    "coal_measure_clay": {
        "description": "Kaolinite + illite + siderite; typical Dhanbad/Jharia coal measure stratigraphy",
        "key_minerals": ["kaolinite", "illite", "siderite"],
        "diagnostic_features": "Kaolinite 2200nm; Illite 2200+2340nm; Siderite 2300nm broad + 1200nm Fe",
    },
    "coal_fire_alteration": {
        "description": "Thermally altered clays + hematite; coal fire zones",
        "key_minerals": ["meta_kaolinite", "hematite"],
        "diagnostic_features": "Shifted clay 2180nm; Hematite 860nm; weakened 1900nm water",
    },
    "acid_mine_drainage": {
        "description": "Jarosite + copiapite + gypsum; AMD indicator minerals",
        "key_minerals": ["jarosite", "gypsum"],
        "diagnostic_features": "Jarosite 2260nm OH-Fe; Gypsum 1900nm strong + 1440-1530nm triplet",
    },
}


def lookup_mineral(name: str) -> MineralExpertProfile | None:
    for profile in MINERAL_FEATURES:
        if profile.name == name:
            return profile
        if name in profile.aliases:
            return profile
    return None


def minerals_for_alteration(alteration_key: str) -> list[MineralExpertProfile]:
    if alteration_key not in ALTERATION_ASSEMBLAGES:
        return []
    keys = ALTERATION_ASSEMBLAGES[alteration_key]["key_minerals"]
    return [p for p in MINERAL_FEATURES if p.name in keys]


def all_mineral_names() -> list[str]:
    return [p.name for p in MINERAL_FEATURES]


def features_table_csv() -> str:
    lines: list[str] = []
    lines.append("mineral_name,group,alteration,position_nm,depth_min,depth_max,fwhm_nm,asymmetry,assignment,notes")
    for profile in MINERAL_FEATURES:
        if not profile.features:
            lines.append(
                f"{profile.name},{profile.group},{profile.alteration},,,,1.0,1.0,no_diagnostic_features,{profile.notes}"
            )
        for feat in profile.features:
            lines.append(
                f"{profile.name},{profile.group},{profile.alteration},"
                f"{feat.position_nm},{feat.depth_min},{feat.depth_max},"
                f"{feat.fwhm_nm},{feat.asymmetry},{feat.assignment},{feat.notes}"
            )
    return "\n".join(lines)
