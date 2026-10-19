# Table 3 for motor experiments (SMASH-MOTOR)

Same structure as Table 3 of the FAIR optical-tweezers guidelines: metadata fields grouped as hardware, assay, construct and solution, with one column per experiment type. **R** required, **O** optional, **–** not applicable. `motor:` = SMASH-MOTOR record field, `smfs:` = field of the linked SMASH-BIO record. Generated from `hub/motors/table3_motor.yaml` (a proposal for the author to edit). Completeness scores count the R cells of a record's experiment type.

Experiment types:

- **OT single bead** (`optical_trap_single_bead`): Optical trap, single bead (bead carries the motor along a surface-bound track)
- **OT three-bead** (`optical_trap_three_bead`): Optical trap, three-bead (actin dumbbell held over a surface pedestal)
- **OT nucleic-acid tether** (`optical_trap_dna_tether`): Optical trap, nucleic-acid tether (dual-trap dumbbell or single trap; polymerases, helicases, packaging, ribosome)
- **Magnetic tweezers** (`magnetic_tweezers`): Magnetic tweezers (bead on a tethered nucleic acid)
- **Flow / curtains** (`flow_stretching`): Flow stretching / DNA curtains
- **SM fluorescence** (`sm_fluorescence`): Single-molecule fluorescence tracking (TIRF, FIONA, MINFLUX), no applied force
- **Gliding / ensemble** (`gliding_ensemble`): Gliding / in vitro motility (ensemble)

| Section | Field | Path | OT single bead | OT three-bead | OT nucleic-acid tether | Magnetic tweezers | Flow / curtains | SM fluorescence | Gliding / ensemble |
| --- | --- | --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| hardware | Make and model of setup | `smfs:hardware.make_of_setup` | O | O | O | O | O | O | O |
| hardware | Detection device | `smfs:hardware.detection_device` | R | R | R | R | R | R | O |
| hardware | Objective lens | `smfs:hardware.objective_lens` | O | O | O | O | O | O | O |
| hardware | Trap laser wavelength | `smfs:hardware.optical.laser_wavelength` | R | R | R | – | – | – | – |
| hardware | Trap stiffness ± uncertainty | `smfs:hardware.optical.trap_stiffness` | R | R | R | – | – | – | – |
| hardware | Magnet configuration | `smfs:hardware.magnetic` | – | – | – | R | – | – | – |
| hardware | Calibration technique | `smfs:hardware.calibration_technique` | R | R | R | R | – | – | – |
| hardware | Acquisition rate | `smfs:hardware.acquisition_rate` | R | R | R | R | R | R | O |
| hardware | Filter frequency | `smfs:hardware.filter_frequency` | R | R | R | O | – | – | – |
| hardware | Temperature | `motor:chemistry.temperature_C|smfs:hardware.temperature` | R | R | R | R | R | R | R |
| assay | Bead or probe size | `smfs:assay.bead_size` | R | R | R | R | – | – | – |
| assay | Motor attachment | `motor:probe_link.attachment` | R | R | R | R | O | – | R |
| assay | Motors per probe | `motor:probe_link.motors_per_probe` | R | R | O | O | O | O | – |
| assay | Single-motor verification | `motor:probe_link.single_motor_verification` | R | R | O | O | O | O | – |
| assay | Load geometry | `motor:load.geometry` | R | R | R | R | O | – | – |
| assay | Load direction | `motor:load.direction` | R | R | R | R | O | – | – |
| assay | Vertical force component considered | `motor:load.vertical_component_considered` | R | O | – | – | – | – | – |
| assay | Feedback (clamp) mode | `motor:feedback.mode` | R | R | R | O | – | – | – |
| assay | Molecules analysed | `motor:reporting.n_molecules` | R | R | R | R | R | R | O |
| assay | Runs analysed | `motor:reporting.n_runs` | R | O | R | O | O | R | – |
| assay | Steps analysed | `motor:reporting.n_steps` | R | R | R | O | – | O | – |
| assay | Step-detection method | `motor:reporting.step_detection` | R | R | R | O | – | O | – |
| assay | Fit models | `motor:reporting.fit_models` | O | O | O | O | O | O | O |
| construct | Motor family | `motor:family` | R | R | R | R | R | R | R |
| construct | Isoform / construct name | `motor:isoform` | R | R | R | R | R | R | R |
| construct | UniProt accession | `motor:uniprot` | R | R | R | R | R | R | R |
| construct | Truncation, tags, mutations | `motor:construct` | R | R | R | R | R | R | R |
| construct | Oligomeric state | `motor:oligomeric_state` | O | O | O | O | O | O | O |
| construct | Adaptors / activators | `motor:adaptors` | O | O | O | O | O | O | O |
| construct | Track type | `motor:track.track_type` | R | R | R | R | R | R | R |
| construct | Track source | `motor:track.track_source` | R | R | R | R | R | R | R |
| construct | Track polarity known | `motor:track.polarity_marked` | R | O | O | O | O | O | O |
| construct | Lattice or sequence | `motor:track.lattice_or_sequence` | O | O | R | R | R | O | O |
| construct | Track decorations | `motor:track.decorations` | O | O | O | O | O | O | O |
| solution | Buffer components | `smfs:solution.components` | R | R | R | R | R | R | R |
| solution | Nucleotide and concentration | `motor:chemistry.nucleotide` | R | R | R | R | R | R | R |
| solution | [ADP], [Pi] | `motor:chemistry.adp_uM` | O | O | O | O | O | O | O |
| solution | Nucleotide analogues | `motor:chemistry.analogues` | O | O | O | O | O | O | O |
| solution | [Mg2+] | `motor:chemistry.mg_mM` | R | R | R | R | R | R | R |
| solution | Ionic strength | `motor:chemistry.ionic_strength_mM` | R | R | R | R | R | R | R |
| solution | Oxygen scavenging | `smfs:solution.oxygen_scavenging` | O | O | O | O | O | R | O |
| solution | Crowders | `motor:chemistry.crowders` | O | O | O | O | O | O | O |
| solution | Inhibitors | `motor:chemistry.inhibitors` | O | O | O | O | O | O | O |

Observables each experiment type usually reports (**E**; informational, not scored):

| Observable | OT single bead | OT three-bead | OT nucleic-acid tether | Magnetic tweezers | Flow / curtains | SM fluorescence | Gliding / ensemble |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| `step_size` | E | E | E | E | – | E | – |
| `stall_force` | E | E | E | E | – | – | – |
| `force_velocity_curve` | E | – | E | E | – | – | – |
| `velocity` | E | – | E | E | E | E | E |
| `processivity_run_length` | E | – | E | E | E | E | – |
| `dwell_time` | E | E | E | E | – | E | – |
| `detachment_force` | E | E | – | – | – | – | – |
| `randomness_parameter` | E | – | E | – | – | E | – |
