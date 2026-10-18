use pull_engine::nakin::*;
use pull_engine::nucleic::{stem_delta_g, Polymer};

fn main() {
    let stem = "GAGTCCTGGATCCTGTCCGC";
    for (t, th) in [(296.15, Thermo::Browser), (296.15, Thermo::Reference)] {
        let sys = NaSystem {
            polymer: Polymer::Dna, construct: Construct::Hairpin, stem: stem.into(), loop_nt: 4,
            temperature_k: t, na_mm: 200.0, mg_mm: 0.0, thermo: th, trap_k_pn_nm: 0.3,
            handle_bp: 1600.0, handle_lp_nm: 50.0, handle_s_pn: 1000.0, ss_rise_nm: 0.59, ss_lp_nm: 0.75,
        };
        let l = Landscape::build(&sys).unwrap();
        println!("{th:?}: stacks {:.2} salt {:.2} loop {:.2} G_N {:.1} pNnm F1/2 {:?}", l.dg_stacks_kcal, l.salt_kcal, l.loop_kcal, l.g_chem[l.n_bp], l.f_half());
    }
    for t in [296.15, 310.15] {
        let s = stem_delta_g(stem, Polymer::Dna, 0.2, t).unwrap();
        println!("T {t}: dg1m {:.2}", s.dg_1m_kcal);
    }
}
