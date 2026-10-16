"""Small, reviewable source-term lists for high-confidence entity extraction.

Every list here is project vocabulary. A term only becomes a graph node when it
occurs in the pinned catalog, in the section named next to each list, so a list
entry that no page mentions produces nothing.
"""
from __future__ import annotations

import re

# --- Concepts: matched in §2 Mathematical Foundations ------------------------
# name -> aliases. An alias with an upper-case letter is matched case-sensitively
# (acronyms such as WAL or MVD); a lower-case alias is matched case-insensitively.
CONCEPTS = {
    "AGM bound": ("AGM bound", "Atserias-Grohe-Marx bound", "fractional edge cover bound"),
    "acyclicity": ("α-acyclicity", "alpha-acyclicity", "β-acyclicity", "gamma-acyclicity"),
    "conjunctive query": ("conjunctive queries", "conjunctive query"),
    "union of conjunctive queries": ("union of conjunctive queries", "unions of conjunctive queries", "UCQ", "UCQs"),
    "first-order logic": ("first-order logic", "FO logic"),
    "monadic second-order logic": ("monadic second-order", "MSO"),
    "Datalog": ("Datalog",),
    "relational algebra": ("relational algebra",),
    "homomorphism": ("homomorphism", "homomorphisms"),
    "query containment": ("query containment",),
    "query rewriting": ("query rewriting",),
    "certain answers": ("certain answers", "certain answer"),
    "the chase": ("the chase", "chase procedure", "chase algorithm"),
    "tuple-generating dependency": ("tuple-generating", "TGD", "TGDs"),
    "denial constraint": ("denial constraint", "denial constraints"),
    "data exchange": ("data exchange",),
    "functional dependency": ("functional dependencies", "functional dependency"),
    "multivalued dependency": ("multivalued dependency", "multivalued dependencies", "MVD", "MVDs"),
    "join dependency": ("join dependency", "join dependencies"),
    "normal form": ("normal form", "BCNF", "3NF", "Boyce-Codd"),
    "hypergraph": ("hypergraphs", "hypergraph"),
    "join tree": ("join trees", "join tree"),
    "treewidth": ("treewidth",),
    "hypertree width": ("hypertree width",),
    "fractional hypertree width": ("fractional hypertree width",),
    "submodular width": ("submodular width",),
    "fractional edge cover": ("fractional edge cover", "fractional edge covers"),
    "worst-case optimal join": ("worst-case optimal join", "worst-case-optimal join", "WCOJ"),
    "submodularity": ("submodularity", "submodular function", "submodular functions"),
    "polymatroid": ("polymatroid", "polymatroids"),
    "entropy": ("entropy",),
    "Shearer's lemma": ("Shearer",),
    "semiring": ("semiring", "semirings"),
    "data provenance": ("provenance semirings", "data provenance"),
    "provenance semiring": ("provenance semiring", "provenance semirings", "semiring provenance"),
    "tree automaton": ("tree automata", "tree automaton"),
    "regular path query": ("regular path query", "regular path queries", "RPQ", "RPQs"),
    "serializability": ("serializability", "serializable"),
    "snapshot isolation": ("snapshot isolation",),
    "two-phase locking": ("two-phase locking", "2PL"),
    "MVCC": ("MVCC", "multi-version concurrency", "multiversion concurrency"),
    "linearizability": ("linearizability", "linearizable"),
    "consistency model": ("consistency model", "consistency models"),
    "causal consistency": ("causal consistency", "causally consistent"),
    "eventual consistency": ("eventual consistency", "eventually consistent"),
    "CRDT": ("CRDT", "CRDTs", "conflict-free replicated"),
    "consensus": ("consensus",),
    "Paxos": ("Paxos",),
    "Raft": ("Raft",),
    "quorum": ("quorum", "quorums"),
    "Byzantine fault tolerance": ("Byzantine",),
    "two-phase commit": ("two-phase commit", "2PC"),
    "TrueTime / HLC": ("TrueTime", "hybrid logical clock", "HLC"),
    "write-ahead logging": ("write-ahead logging", "write-ahead log", "WAL"),
    "ARIES": ("ARIES",),
    "B-tree": ("B-tree", "B-trees", "B+-tree", "B+ tree"),
    "LSM-tree": ("LSM-tree", "LSM tree", "log-structured merge"),
    "R-tree": ("R-tree", "R-trees", "R*-tree"),
    "space-filling curve": ("space-filling curve", "space-filling curves", "Z-order", "Hilbert curve"),
    "Bloom filter": ("Bloom filter", "Bloom filters"),
    "sketch (streaming)": ("sketch", "sketches", "streaming sketch"),
    "HyperLogLog": ("HyperLogLog",),
    "Count-Min sketch": ("Count-Min", "CountMin"),
    "histogram": ("histogram", "histograms"),
    "sampling": ("sampling",),
    "reservoir sampling": ("reservoir sampling",),
    "cardinality estimation": ("cardinality estimation", "cardinality estimate"),
    "Chernoff bound": ("Chernoff", "Hoeffding"),
    "VC dimension": ("VC dimension", "VC-dimension", "Vapnik"),
    "Zipf distribution": ("Zipf", "Zipfian"),
    "locality-sensitive hashing": ("locality-sensitive hashing", "LSH"),
    "nearest neighbor search": ("nearest neighbor", "nearest-neighbor", "k-NN", "kNN"),
    "HNSW": ("HNSW",),
    "product quantization": ("product quantization",),
    "cache-oblivious": ("cache-oblivious",),
    "external-memory model": ("external-memory model", "external memory model", "I/O model"),
    "competitive analysis": ("competitive ratio", "competitive analysis"),
    "queueing theory": ("queueing", "queuing"),
    "differential privacy": ("differential privacy", "differentially private"),
    "ORAM": ("ORAM", "oblivious RAM"),
    "secure multiparty computation": ("secure multiparty", "secure multi-party", "MPC protocol"),
    "trusted execution environment": ("trusted execution", "SGX", "enclave"),
    "linear programming": ("linear program", "linear programming", "LP relaxation"),
    "matrix multiplication": ("matrix multiplication",),
    "tensor": ("tensor", "tensors"),
    "Lipschitz": ("Lipschitz",),
    "Markov decision process": ("Markov decision process", "MDP"),
    "Bayesian optimization": ("Bayesian optimization",),
    "bitemporal model": ("bitemporal",),
    "Allen's interval algebra": ("Allen's interval", "interval algebra"),
}

# --- Concept hierarchy (GENERALIZES, broader -> narrower) ---------------------
# Project vocabulary, like the taxonomy terms: textbook relations between the
# concepts above, each with its rationale. An edge is emitted only when both
# concepts occur in the graph.
CONCEPT_HIERARCHY = (
    ("submodular width", "fractional hypertree width",
     "subw(H) <= fhw(H) for every hypergraph H; submodular width is the coarser tractability measure "
     "(Marx, JACM 2013)."),
    ("fractional hypertree width", "hypertree width",
     "fhw(H) <= ghw(H) <= hw(H): fractional hypertree width relaxes the integral edge cover of hypertree width "
     "(Grohe-Marx 2014)."),
    ("hypertree width", "treewidth",
     "Hypertree width extends treewidth from graphs to hypergraphs; bounded treewidth implies bounded hypertree width "
     "(Gottlob-Leone-Scarcello 2002)."),
    ("hypertree width", "acyclicity",
     "A hypergraph is alpha-acyclic exactly when its (generalized) hypertree width is 1."),
    ("acyclicity", "join tree",
     "A conjunctive query is alpha-acyclic exactly when it has a join tree."),
    ("union of conjunctive queries", "conjunctive query",
     "A conjunctive query is a union of conjunctive queries with one member."),
    ("Datalog", "union of conjunctive queries",
     "Non-recursive Datalog expresses exactly the unions of conjunctive queries."),
    ("first-order logic", "conjunctive query",
     "Conjunctive queries are the existential-conjunctive fragment of first-order logic."),
    ("join dependency", "multivalued dependency",
     "A multivalued dependency is a binary join dependency."),
    ("multivalued dependency", "functional dependency",
     "Every functional dependency X -> Y implies the multivalued dependency X ->> Y."),
    ("tuple-generating dependency", "join dependency",
     "Join dependencies are expressible as full tuple-generating dependencies."),
    ("semiring", "provenance semiring",
     "Provenance semirings are commutative semirings used to annotate query answers "
     "(Green-Karvounarakis-Tannen 2007)."),
    ("data provenance", "provenance semiring",
     "Semiring provenance is one model of data provenance."),
    ("consensus", "Paxos", "Paxos is a consensus protocol."),
    ("consensus", "Raft", "Raft is a consensus protocol."),
    ("consensus", "Byzantine fault tolerance", "Byzantine agreement is consensus under arbitrary faults."),
    ("consistency model", "linearizability", "Linearizability is a consistency model."),
    ("consistency model", "causal consistency", "Causal consistency is a consistency model."),
    ("consistency model", "eventual consistency", "Eventual consistency is a consistency model."),
    ("consistency model", "serializability", "Serializability is the transactional consistency model."),
    ("consistency model", "snapshot isolation", "Snapshot isolation is a transactional consistency (isolation) model."),
    ("sketch (streaming)", "HyperLogLog", "HyperLogLog is a cardinality sketch."),
    ("sketch (streaming)", "Count-Min sketch", "Count-Min is a frequency sketch."),
    ("sketch (streaming)", "Bloom filter", "A Bloom filter is a membership sketch."),
    ("sampling", "reservoir sampling", "Reservoir sampling is a streaming sampling scheme."),
    ("nearest neighbor search", "HNSW", "HNSW is a graph index for approximate nearest neighbor search."),
    ("nearest neighbor search", "locality-sensitive hashing",
     "LSH is a hashing scheme for approximate nearest neighbor search."),
    ("nearest neighbor search", "product quantization",
     "Product quantization compresses vectors for nearest neighbor search."),
    ("submodularity", "polymatroid", "A polymatroid is defined by a monotone submodular rank function."),
    ("entropy", "Shearer's lemma", "Shearer's lemma is an entropy inequality."),
    ("fractional edge cover", "AGM bound", "The AGM bound is the size bound given by a fractional edge cover."),
)

# --- Systems and algorithms: plain-text matches in §3 -------------------------
# Bold names in §3 are found by etl/sota_entities.py; these lists catch the
# most common systems when they are written without bold.
SYSTEMS = (
    "BigQuery", "CockroachDB", "DuckDB", "HyPer", "LogicBlox", "MariaDB",
    "MonetDB", "MySQL", "PostgreSQL", "Presto", "Redshift", "Snowflake",
    "Spark SQL", "SQLite", "TiDB", "Trino", "Umbra", "Spanner", "ClickHouse",
    "SAP HANA", "YugabyteDB", "FoundationDB", "Cassandra", "MongoDB", "RocksDB",
    "LevelDB", "Hekaton", "Silo", "Calvin", "Aurora", "Neo4j", "Velox", "DataFusion",
    "Apache Calcite", "Apache Arrow", "Apache Flink", "Kafka", "Materialize", "Druid",
    "Pinot", "Vertica", "Oracle Database", "SQL Server", "DB2", "Socrates", "Neon",
    "PolarDB", "FaRM", "RAMCloud", "Milvus", "FAISS", "Weaviate", "TimescaleDB",
    "InfluxDB", "Kùzu", "Photon", "Delta Lake", "Apache Iceberg", "Hudi",
)

ALGORITHMS = (
    "GYO reduction", "Leapfrog Triejoin", "Generic Join", "InsideOut algorithm",
    "Yannakakis algorithm", "maximum-cardinality search", "Bao", "Neo", "Balsa",
    "PANDA", "Cascades", "Volcano", "Eddies", "Free Join",
)

# --- Computation models: matched in §4 and §5 ---------------------------------
# name -> (class code, regex patterns)
MODELS = {
    "word-RAM": ("word-ram", (r"\bword[- ]RAM\b", r"\bRAM model\b", r"\bunit-cost RAM\b")),
    "cell-probe": ("cell-probe", (r"\bcell[- ]probe\b",)),
    "external-memory": ("external-memory", (r"\bexternal[- ]memory(?: model)?\b",)),
    "I/O": ("external-memory", (r"\bI/O model\b", r"\bexternal-memory I/Os\b")),
    "comparison": ("comparison", (r"\bcomparison[- ]based model\b", r"\bcomparison model\b")),
    "streaming": ("streaming", (r"\bstreaming model\b", r"\bone[- ]pass\b", r"\bsingle[- ]pass\b")),
    "PRAM": ("parallel", (r"\bPRAM\b", r"\bparallel RAM\b")),
    "MPC": ("parallel", (r"\bMPC model\b", r"\bmassively parallel computation\b", r"\bload per server\b")),
    "Turing machine": ("turing", (r"\bTuring machine model\b",)),
    "SETH / fine-grained": ("fine-grained", (r"\bSETH\b", r"\b3SUM\b", r"\bAPSP\b", r"\bOMv\b",
                                             r"\bfine[- ]grained (?:complexity|hardness|lower bound)s?\b")),
    "NP / classical": ("complexity-class", (r"\bNP-hard", r"\bNP-complete", r"\bcoNP", r"\bPSPACE",
                                            r"\bEXPTIME", r"#P-(?:hard|complete)", r"\bW\[1\]", r"\bundecidab")),
    "information-theoretic": ("information-theoretic", (r"\binformation[- ]theoretic", r"\bentropy\b")),
    "CAP / FLP impossibility": ("distributed-impossibility", (r"\bCAP\b", r"\bFLP\b", r"\bPACELC\b")),
    "competitive (online)": ("online", (r"\bcompetitive ratio\b", r"\bcompetitive analysis\b",
                                        r"\b(?:is|are|be) \d*-?competitive\b")),
    "communication complexity": ("communication", (r"\bcommunication complexity\b",)),
    "cryptographic": ("cryptographic", (r"\bIND-CPA\b", r"\bsemantic security\b", r"\bleakage[- ]abuse\b",
                                        r"\boblivious\b", r"\bcryptographic\b")),
    "statistical": ("statistical", (r"\bsample complexity\b", r"\bminimax\b", r"\bestimation error\b")),
}

# --- Institutions: matched in §7 Current Research -----------------------------
# (key, display name, kind, regex). Kinds follow the Institution.kind code list.
INSTITUTIONS = (
    ("cmu", "Carnegie Mellon University", "academic", r"\bCMU\b|Carnegie Mellon"),
    ("mit", "MIT", "academic", r"\bMIT\b(?!\s+[Ll]icen[cs]e)|\bCSAIL\b|\bDSAIL\b"),
    ("uw", "University of Washington", "academic", r"University of Washington|\bUW\b(?![\s–-]*Madison)"),
    ("wisconsin", "University of Wisconsin–Madison", "academic", r"\bWisconsin\b|\bUW[\s–-]*Madison\b"),
    ("berkeley", "UC Berkeley", "academic", r"\bBerkeley\b|\bRISELab\b|\bAMPLab\b"),
    ("stanford", "Stanford University", "academic", r"\bStanford\b"),
    ("tum", "TU Munich", "academic", r"\bTUM\b|TU Munich|TU München"),
    ("cwi", "CWI", "academic", r"\bCWI\b"),
    ("epfl", "EPFL", "academic", r"\bEPFL\b"),
    ("eth", "ETH Zurich", "academic", r"\bETH\b"),
    ("uzh", "University of Zurich", "academic", r"(?<!ETH )\bZ(?:u|ü)rich\b"),
    ("waterloo", "University of Waterloo", "academic", r"\bWaterloo\b"),
    ("toronto", "University of Toronto", "academic", r"\bToronto\b"),
    ("nus", "National University of Singapore", "academic", r"\bNUS\b"),
    ("tsinghua", "Tsinghua University", "academic", r"\bTsinghua\b"),
    ("pku", "Peking University", "academic", r"\bPeking\b|\bPKU\b"),
    ("cuhk", "CUHK", "academic", r"\bCUHK\b"),
    ("hkust", "HKUST", "academic", r"\bHKUST\b"),
    ("harvard", "Harvard University", "academic", r"\bHarvard\b"),
    ("yale", "Yale University", "academic", r"\bYale\b"),
    ("cornell", "Cornell University", "academic", r"\bCornell\b"),
    ("princeton", "Princeton University", "academic", r"\bPrinceton\b"),
    ("duke", "Duke University", "academic", r"\bDuke\b"),
    ("brown", "Brown University", "academic", r"\bBrown\b(?= ?[,;)/(])"),
    ("columbia", "Columbia University", "academic", r"\bColumbia\b"),
    ("nyu", "NYU", "academic", r"\bNYU\b"),
    ("bu", "Boston University", "academic", r"\bBU\b|Boston University"),
    ("umass", "UMass Amherst", "academic", r"\bUMass\b"),
    ("northeastern", "Northeastern University", "academic", r"\bNortheastern\b"),
    ("stonybrook", "Stony Brook University", "academic", r"Stony Brook"),
    ("buffalo", "University at Buffalo", "academic", r"\bBuffalo\b"),
    ("ucsd", "UC San Diego", "academic", r"\bUCSD\b|UC San Diego"),
    ("ucla", "UCLA", "academic", r"\bUCLA\b"),
    ("ucsc", "UC Santa Cruz", "academic", r"\bUCSC\b|UC Santa Cruz"),
    ("ucr", "UC Riverside", "academic", r"UC Riverside|\bUCR\b"),
    ("uiuc", "UIUC", "academic", r"\bUIUC\b|\bIllinois\b"),
    ("michigan", "University of Michigan", "academic", r"\bMichigan\b"),
    ("penn", "University of Pennsylvania", "academic", r"\bUPenn\b|University of Pennsylvania"),
    ("chicago", "University of Chicago", "academic", r"\bUChicago\b|University of Chicago|\bChicago\b"),
    ("umd", "University of Maryland", "academic", r"\bUMD\b|\bMaryland\b"),
    ("utaustin", "UT Austin", "academic", r"UT[ -]Austin"),
    ("purdue", "Purdue University", "academic", r"\bPurdue\b"),
    ("gatech", "Georgia Tech", "academic", r"Georgia Tech"),
    ("oxford", "University of Oxford", "academic", r"\bOxford\b"),
    ("edinburgh", "University of Edinburgh", "academic", r"\bEdinburgh\b"),
    ("warwick", "University of Warwick", "academic", r"\bWarwick\b"),
    ("imperial", "Imperial College London", "academic", r"\bImperial College\b"),
    ("saarland", "Saarland University", "academic", r"\bSaarland\b"),
    ("darmstadt", "TU Darmstadt", "academic", r"\bDarmstadt\b"),
    ("hpi", "Hasso Plattner Institute", "academic", r"\bHPI\b|Hasso Plattner"),
    ("tuberlin", "TU Berlin", "academic", r"\bTU Berlin\b"),
    ("tuwien", "TU Wien", "academic", r"\bTU Wien\b"),
    ("mpi", "Max Planck Institute", "academic", r"Max Planck|\bMPI\b(?!-)"),
    ("inria", "Inria", "academic", r"\bINRIA\b|\bInria\b"),
    ("irif", "IRIF (Université Paris Cité)", "academic", r"\bIRIF\b"),
    ("eurecom", "EURECOM", "academic", r"\bEURECOM\b"),
    ("aarhus", "Aarhus University", "academic", r"\bAarhus\b"),
    ("copenhagen", "University of Copenhagen", "academic", r"\bCopenhagen\b"),
    ("pisa", "University of Pisa", "academic", r"\bPisa\b"),
    ("technion", "Technion", "academic", r"\bTechnion\b"),
    ("kaist", "KAIST", "academic", r"\bKAIST\b"),
    ("anu", "Australian National University", "academic", r"\bANU\b"),
    ("iit", "IIT", "academic", r"\bIIT\b"),
    ("imfd", "IMFD / PUC Chile", "academic", r"\bIMFD\b|\bPUC\b"),
    ("microsoft", "Microsoft", "industry", r"\bMicrosoft\b|\bMSR\b"),
    ("google", "Google", "industry", r"\bGoogle\b"),
    ("amazon", "Amazon (AWS)", "industry", r"\bAmazon\b|\bAWS\b"),
    ("oracle", "Oracle", "industry", r"\bOracle\b"),
    ("ibm", "IBM", "industry", r"\bIBM\b"),
    ("meta", "Meta (Facebook)", "industry", r"\bMeta\b(?!-)|\bFacebook\b"),
    ("apple", "Apple", "industry", r"\bApple\b"),
    ("alibaba", "Alibaba", "industry", r"\bAlibaba\b"),
    ("databricks", "Databricks", "industry", r"\bDatabricks\b"),
    ("sap", "SAP", "industry", r"\bSAP\b(?!\s+HANA)"),
    ("intel", "Intel", "industry", r"\bIntel\b"),
    ("nvidia", "NVIDIA", "industry", r"\bNVIDIA\b|\bNvidia\b"),
    ("vmware", "VMware", "industry", r"\bVMware\b"),
    ("cockroachlabs", "Cockroach Labs", "industry", r"Cockroach Labs"),
    ("pingcap", "PingCAP", "industry", r"\bPingCAP\b"),
    ("relationalai", "RelationalAI", "industry", r"\bRelationalAI\b"),
    ("megagon", "Megagon Labs", "industry", r"Megagon"),
    ("samsung", "Samsung", "industry", r"\bSamsung\b"),
    ("nist", "NIST", "government", r"\bNIST\b"),
)

# --- Venue kinds ---------------------------------------------------------------
CONFERENCE_VENUES = (
    "SIGMOD", "VLDB", "PVLDB", "PODS", "ICDE", "EDBT", "ICDT", "CIDR", "SoCC", "DaMoN",
    "SOSP", "OSDI", "NSDI", "EuroSys", "ATC", "FAST", "ASPLOS", "ISCA", "MICRO", "HPCA",
    "SODA", "STOC", "FOCS", "ICALP", "PODC", "DISC", "SPAA", "ESA", "LICS", "KR", "IJCAI",
    "AAAI", "NeurIPS", "NIPS", "ICML", "ICLR", "KDD", "WWW", "CIKM", "WSDM", "SIGIR", "CCS",
    "S&P", "USENIX Security", "NDSS", "CRYPTO", "EUROCRYPT", "SIGCOMM", "MobiSys", "SIGSPATIAL",
    "GIS", "SSTD", "SSDBM", "DEBS", "Middleware", "SC", "PPoPP", "ICS", "IPDPS", "SIGMETRICS",
    "SRDS", "DSN", "CAV", "POPL", "PLDI", "OOPSLA", "ICSE", "FSE", "ISSTA", "RTSS", "SIGGRAPH",
    "CVPR", "ICCV", "ACL", "EMNLP", "NAACL", "UAI", "AISTATS", "COLT", "ITCS", "APPROX", "IPCO",
    "SoCG", "WADS", "SWAT", "MFCS", "STACS", "CSL", "CONCUR", "TACAS", "VMCAI", "SAT", "CP",
    "ASIACRYPT", "TCC", "CoNEXT", "SSS", "ESOP", "OPODIS", "ADBIS", "HotNets", "HotOS", "HotStorage",
    "HotCloud", "ICDCS", "ECOOP", "PPDP", "PaPoC", "PDIS", "ALENEX", "USENIX", "CT-RSA", "SIGOPS",
    "Onward", "ICDM", "SDM", "PAKDD", "ECML", "DASFAA", "WISE", "ER", "CAiSE", "DEXA", "SSTD", "MDM",
    "ICPE", "IISWC", "ISPASS", "LCTES", "CGO", "CC", "EuroPar", "Euro-Par", "HPDC", "CLUSTER", "CCGrid",
    "IPSN", "SenSys", "INFOCOM", "ICNP", "SIGSAC", "PETS", "PoPETs", "ACSAC", "ESORICS", "AsiaCCS",
)
JOURNAL_PATTERNS = (
    r"\bjournal\b", r"\btransactions\b", r"\bTODS\b", r"\bJACM\b", r"\bVLDB ?J\b", r"\bVLDBJ\b",
    r"\bSICOMP\b", r"\bSIAM J", r"\bTKDE\b", r"\bTOCS\b", r"\bCACM\b", r"\bCommunications of the ACM\b",
    r"\bSIGMOD Record\b", r"\bIEEE Data Eng", r"\bData Eng\. Bull", r"\bFoundations and Trends\b",
    r"\bTCS\b", r"\bTheoretical Computer Science\b", r"\bInformation Systems\b", r"\bAlgorithmica\b",
    r"\bDistributed Computing\b", r"\bTOPLAS\b", r"\bTALG\b", r"\bTOCL\b", r"\bJCSS\b", r"\bLMCS\b",
    r"\bInf\. Process\. Lett", r"\bIPL\b", r"\bACM Comput\. Surv", r"\bComputing Surveys\b", r"\bPACMMOD\b",
    r"\bProc\. ACM Manag\. Data\b", r"\bNature\b", r"\bScience\b", r"\bJMLR\b", r"\bTPAMI\b",
)
PREPRINT_PATTERNS = (r"\barxiv\b", r"\bcorr\b", r"\bpreprint\b", r"\beprint\b", r"\biacr\b", r"\bssrn\b")
JOURNAL_PATTERNS += (
    r"\bJ\. ", r"\bTrans\.", r"\bAnnals\b", r"^Artificial Intelligence$",
    r"\bInformation and (?:Computation|Control)\b",
    r"\bJAIR\b", r"\bEJOR\b", r"\bEconometrica\b", r"\bInternet Mathematics\b", r"\bData & Knowledge Engineering\b",
    r"\bDistributed and Parallel Databases\b", r"\bSoftware: Practice", r"\bIEEE Computer\b", r"\bTLDKS\b",
    r"\bMathematics\b", r"\bReview\b", r"\bLetters\b", r"\bMagazine\b", r"\bBulletin\b", r"\bQuarterly\b",
    r"^CC$", r"\bIJACSA\b", r"\bPVLDB\b", r"\bProc\. VLDB Endow",
    r"\bACM T[A-Z]{2,}\b", r"\bIEEE T[A-Z]{2,}\b", r"\bActa\b", r"\bMathematical Programming\b",
    r"\bReal-Time Systems\b", r"\bFuture Generation Computer Systems\b", r"\bJPDC\b", r"^Machine Learning$",
    r"\bData Mining and Knowledge Discovery\b", r"\bSIGACT News\b", r"\bAdvances in\b", r"\bJEA\b",
    r"\bComputer Networks\b", r"\bCommunications\b", r"\bJournal\b", r"\bPeer-to-Peer\b",
    r"\bACM SIG\w+ (?:News|Record|Review)\b",
)
BOOK_PATTERNS = (r"Addison-Wesley", r"Morgan (?:&|and) Claypool", r"University Press|Univ\. Press", r"\bSpringer\b",
                 r"\bWiley\b", r"\bElsevier\b", r"\bO'Reilly\b", r"\bMIT Press\b", r"\bPrentice", r"\bMcGraw",
                 r"\bbook\b", r"\bSynthesis Lectures\b", r"\bLecture Notes\b", r"\bReasoning Web\b", r"\bchapter",
                 r"\bFreeman\b", r"\bMorgan Kaufmann\b", r"\bCRC\b", r"\bNow Publishers\b", r"\bTractability\b")
REPORT_PATTERNS = (r"\bTechnical report\b", r"\bTech\.? ?Rep", r"\bthesis\b", r"\bPh\.?D\b", r"\bdissertation\b",
                   r"\bwhite ?paper\b", r"\bResearch\b$", r"\bblog\b", r"\bdocumentation\b", r"\bmanual\b", r"\bRFC\b",
                   r"-TR\b", r"\bRR-?\d", r"\bRJ\b", r"\bNIST\b", r"\bSummit\b", r"\btalk\b", r"\bkeynote\b")

# --- Topic -> technique family crosswalk (fallback when the name gives no family) --
TOPIC_TECHNIQUE_FAMILY = {
    "01": "decomposition", "02": "query-optimization", "03": "query-engine", "04": "indexing",
    "05": "transaction-processing", "06": "storage", "07": "storage", "08": "distributed-processing",
    "09": "distributed-processing", "10": "distributed-processing", "11": "storage",
    "12": "transaction-processing", "13": "analytics", "14": "transaction-processing",
    "15": "analytics", "16": "analytics", "17": "analytics", "18": "streaming-system",
    "19": "query-engine", "20": "indexing", "21": "query-engine", "22": "analytics",
    "23": "other", "24": "other", "25": "query-engine", "26": "query-optimization",
    "27": "query-optimization", "28": "indexing", "29": "query-engine",
    "30": "distributed-processing", "31": "storage", "32": "storage", "33": "other",
    "34": "decomposition", "35": "query-optimization",
}

# --- Topic -> problem type crosswalk (fallback when no statement rule fires) ----
TOPIC_PROBLEM_TYPE = {
    "01": "data-modeling", "02": "query-optimization", "03": "query-evaluation",
    "04": "storage-indexing", "05": "transaction-processing", "06": "transaction-processing",
    "07": "storage-indexing", "08": "distributed-data", "09": "distributed-data",
    "10": "distributed-data", "11": "storage-indexing", "12": "distributed-data",
    "13": "analytics", "14": "system-design", "15": "data-integration",
    "16": "data-integration", "17": "analytics", "18": "query-evaluation",
    "19": "data-modeling", "20": "query-evaluation", "21": "query-evaluation",
    "22": "data-modeling", "23": "system-design", "24": "system-design",
    "25": "query-evaluation", "26": "query-optimization", "27": "system-design",
    "28": "query-evaluation", "29": "system-design", "30": "system-design",
    "31": "storage-indexing", "32": "data-modeling", "33": "system-design",
    "34": "data-modeling", "35": "system-design",
}


def _alias_pattern(alias: str) -> re.Pattern:
    needle = re.escape(alias).replace(r"\ ", r"\s+")
    flags = 0 if any(ch.isupper() for ch in alias) else re.IGNORECASE
    return re.compile(r"(?<!\w)" + needle + r"(?!\w)", flags)


_CONCEPT_PATTERNS = {name: tuple(_alias_pattern(a) for a in aliases)
                     for name, aliases in CONCEPTS.items()}
_INSTITUTION_PATTERNS = tuple((key, name, kind, re.compile(pattern))
                              for key, name, kind, pattern in INSTITUTIONS)


def matching_terms(text: str, terms: tuple[str, ...] | list[str]) -> list[str]:
    found = []
    folded = text.casefold()
    for term in terms:
        needle = re.escape(term.casefold()).replace(r"\ ", r"\s+")
        if re.search(r"(?<!\w)" + needle + r"(?!\w)", folded):
            found.append(term)
    return found


def matching_concepts(text: str) -> list[str]:
    return [name for name, patterns in _CONCEPT_PATTERNS.items()
            if any(pattern.search(text) for pattern in patterns)]


def matching_models(text: str) -> list[str]:
    return [model for model, (_, patterns) in MODELS.items()
            if any(re.search(pattern, text, re.IGNORECASE if pattern.islower() else 0) for pattern in patterns)]


def model_class_code(name: str) -> str:
    return MODELS.get(name, ("unclassified", ()))[0]


def matching_institutions(text: str) -> list[tuple[str, str, str]]:
    """(key, name, kind) for every listed institution the text names, in list order."""
    return [(key, name, kind) for key, name, kind, pattern in _INSTITUTION_PATTERNS
            if pattern.search(text)]


def institution_spans(text: str) -> list[tuple[int, int, str]]:
    """(start, end, key) of every institution mention, for locating affiliations."""
    spans = []
    for key, _, _, pattern in _INSTITUTION_PATTERNS:
        spans.extend((m.start(), m.end(), key) for m in pattern.finditer(text))
    return sorted(spans)


def venue_kind_code(name: str) -> str:
    folded = name.casefold()
    if any(re.search(p, folded) for p in PREPRINT_PATTERNS):
        return "preprint"
    if any(re.search(p, name, re.IGNORECASE) for p in REPORT_PATTERNS):
        return "report"
    if any(re.search(p, name, re.IGNORECASE) for p in BOOK_PATTERNS):
        return "book"
    if any(re.search(p, name, re.IGNORECASE) for p in JOURNAL_PATTERNS):
        return "journal"
    tokens = set(re.findall(r"[A-Za-z&]+", name))
    if tokens & set(CONFERENCE_VENUES) or re.search(
            r"\b(conference|conf\.?|proceedings|symposium|workshop|proc\.|ieee \w+|btw|aofa|icm|isit)\b", folded):
        return "conference"
    return "other"
