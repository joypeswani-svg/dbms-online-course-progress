#!/usr/bin/env python3
"""
Regenerate RDR2 seed data and update scripts/build_seed_sql.py.
Features:
- Role-prefixed IDs:
    Admin: A01
    Instructors: I01, I02, I03, I04, I05
    Learners: L01, L02, ..., L20
- Removed avatar_url completely.
- Characters from Red Dead Redemption 2.
"""

import hashlib
import os

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def escape_sql(text: str) -> str:
    if text is None:
        return "NULL"
    return "'" + str(text).replace("'", "''") + "'"

def generate_seed_sql():
    lines = []
    lines.append("-- ============================================================================")
    lines.append("-- Project 34: Online Course Learning Progress Management System")
    lines.append("-- Red Dead Redemption 2 Themed Comprehensive Production Seed Data")
    lines.append("-- Role-Prefixed IDs (A01, I01-I05, L01-L20) & No avatar_url")
    lines.append("-- ============================================================================\n")
    lines.append("USE `course_progress_db`;\n")
    lines.append("SET FOREIGN_KEY_CHECKS = 0;")
    lines.append("TRUNCATE TABLE `feedback`;")
    lines.append("TRUNCATE TABLE `certificates`;")
    lines.append("TRUNCATE TABLE `responses`;")
    lines.append("TRUNCATE TABLE `attempts`;")
    lines.append("TRUNCATE TABLE `questions`;")
    lines.append("TRUNCATE TABLE `quizzes`;")
    lines.append("TRUNCATE TABLE `lesson_progress`;")
    lines.append("TRUNCATE TABLE `enrolments`;")
    lines.append("TRUNCATE TABLE `lessons`;")
    lines.append("TRUNCATE TABLE `modules`;")
    lines.append("TRUNCATE TABLE `courses`;")
    lines.append("TRUNCATE TABLE `learners`;")
    lines.append("TRUNCATE TABLE `instructors`;")
    lines.append("TRUNCATE TABLE `users`;")
    lines.append("SET FOREIGN_KEY_CHECKS = 1;\n")

    # 1. USERS (1 admin, 5 instructors, 20 learners = 26 users)
    users_data = [
        # Admin (A01)
        ("A01", "Dutch van der Linde", "dutch@vanderlinde.com", hash_pw("admin123"), "admin", "2025-10-01 09:00:00"),
        
        # Instructors (I01-I05)
        ("I01", "Hosea Matthews", "hosea@vanderlinde.com", hash_pw("instructor123"), "instructor", "2025-10-02 10:30:00"),
        ("I02", "Arthur Morgan", "arthur@vanderlinde.com", hash_pw("instructor123"), "instructor", "2025-10-03 11:15:00"),
        ("I03", "Sadie Adler", "sadie@adlerbounty.com", hash_pw("instructor123"), "instructor", "2025-10-04 14:00:00"),
        ("I04", "Charles Smith", "charles@wapiti.org", hash_pw("instructor123"), "instructor", "2025-10-05 16:45:00"),
        ("I05", "John Marston", "john@beechershope.com", hash_pw("instructor123"), "instructor", "2025-10-06 08:20:00"),

        # Learners (L01-L20)
        ("L01", "Micah Bell", "micah@bellgang.com", hash_pw("learner123"), "learner", "2025-10-15 11:00:00"),
        ("L02", "Lenny Summers", "lenny@vanderlinde.com", hash_pw("learner123"), "learner", "2025-10-18 13:20:00"),
        ("L03", "Sean MacGuire", "sean@irishrebel.com", hash_pw("learner123"), "learner", "2025-10-22 09:10:00"),
        ("L04", "Javier Escuella", "javier@revolucion.mx", hash_pw("learner123"), "learner", "2025-10-25 15:40:00"),
        ("L05", "Bill Williamson", "bill@williamson.com", hash_pw("learner123"), "learner", "2025-11-01 10:00:00"),
        ("L06", "Abigail Roberts", "abigail@marstonfamily.com", hash_pw("learner123"), "learner", "2025-11-05 14:15:00"),
        ("L07", "Jack Marston", "jack@blackwater.edu", hash_pw("learner123"), "learner", "2025-11-10 11:30:00"),
        ("L08", "Uncle", "uncle@lumbago.org", hash_pw("learner123"), "learner", "2025-11-14 16:50:00"),
        ("L09", "Karen Jones", "karen@vanderlinde.com", hash_pw("learner123"), "learner", "2025-11-20 08:45:00"),
        ("L10", "Mary-Beth Gaskill", "marybeth@romancepress.com", hash_pw("learner123"), "learner", "2025-11-25 12:10:00"),
        ("L11", "Tilly Jackson", "tilly@saint-denis.com", hash_pw("learner123"), "learner", "2025-12-01 09:25:00"),
        ("L12", "Leopold Strauss", "strauss@usuryfinance.com", hash_pw("learner123"), "learner", "2025-12-05 17:35:00"),
        ("L13", "Josiah Trelawny", "trelawny@rhodesmagic.com", hash_pw("learner123"), "learner", "2025-12-10 13:00:00"),
        ("L14", "Reverend Swanson", "swanson@rhodeschurch.org", hash_pw("learner123"), "learner", "2025-12-18 10:40:00"),
        ("L15", "Susan Grimshaw", "susan@camporder.org", hash_pw("learner123"), "learner", "2026-01-08 14:20:00"),
        ("L16", "Simon Pearson", "pearson@rhodesprovisions.com", hash_pw("learner123"), "learner", "2026-01-15 11:15:00"),
        ("L17", "Kieran Duffy", "kieran@horsesandstables.com", hash_pw("learner123"), "learner", "2026-01-22 16:30:00"),
        ("L18", "Molly O'Shea", "molly@dublinheart.com", hash_pw("learner123"), "learner", "2026-02-02 09:50:00"),
        ("L19", "Colm O'Driscoll", "colm@odriscollboys.com", hash_pw("learner123"), "learner", "2026-02-14 15:10:00"),
        ("L20", "Leviticus Cornwall", "leviticus@cornwallkerosene.com", hash_pw("learner123"), "learner", "2026-03-01 10:45:00")
    ]

    lines.append("-- 1. Insert Users")
    lines.append("INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `role`, `created_at`) VALUES")
    user_rows = []
    for u in users_data:
        user_rows.append(f"  ({escape_sql(u[0])}, {escape_sql(u[1])}, {escape_sql(u[2])}, {escape_sql(u[3])}, {escape_sql(u[4])}, {escape_sql(u[5])})")
    lines.append(",\n".join(user_rows) + ";\n")

    # 2. INSTRUCTORS (5)
    instructors_data = [
        ("I01", "I01", "Master Strategist & Enterprise Systems Architect", "Relational Theory, Distributed Architectures, High-Stakes Planning", "Senior tactician of the Van der Linde gang with decades of expertise in architecture and con-artist engineering."),
        ("I02", "I02", "Staff Systems Reliability & Field Operations Engineer", "Fault-Tolerant Infrastructure, Resilient Workflows, Practical Problem Solving", "Lead enforcer and senior engineer ensuring reliable operations in the most hostile environments."),
        ("I03", "I03", "VP of DevSecOps & Threat Hunting", "Zero-Trust Security, Vulnerability Mitigation, High-Velocity Defense", "Fierce bounty hunter turned cybersecurity architect specializing in zero-trust defense."),
        ("I04", "I04", "Principal AI & Environmental Systems Engineer", "Neural Networks, Wildlife Tracking Models, Ethical Machine Learning", "Master tracker and environmental systems specialist building principled machine learning models."),
        ("I05", "I05", "Staff Infrastructure & Ranch DevOps Architect", "Kubernetes, Distributed Storage, Resilient Recovery", "Veteran survivor and infrastructure architect at Beecher's Hope building durable systems.")
    ]
    lines.append("-- 2. Insert Instructors")
    lines.append("INSERT INTO `instructors` (`id`, `user_id`, `title`, `expertise`, `bio`) VALUES")
    inst_rows = []
    for inst in instructors_data:
        inst_rows.append(f"  ({escape_sql(inst[0])}, {escape_sql(inst[1])}, {escape_sql(inst[2])}, {escape_sql(inst[3])}, {escape_sql(inst[4])})")
    lines.append(",\n".join(inst_rows) + ";\n")

    # 3. LEARNERS (20)
    learners_data = [
        ("L01", "L01", "Surveillance & Infiltration Specialist"),
        ("L02", "L02", "Junior Distributed Systems Developer"),
        ("L03", "L03", "FastAPI & Microservice Explorer"),
        ("L04", "L04", "Applied Cryptography & Secure Routing"),
        ("L05", "L05", "Heavy Infrastructure & Scalability Engineer"),
        ("L06", "L06", "Fintech Data Analyst & Accounting Systems"),
        ("L07", "L07", "Computer Science Student & Literature Scholar"),
        ("L08", "L08", "Low-Effort Cloud Automation & Sloth Systems"),
        ("L09", "L09", "Frontend Performance & Event-Driven UI"),
        ("L10", "L10", "Documentation Lead & Information Architecture"),
        ("L11", "L11", "High-Throughput Message Queue Engineer"),
        ("L12", "L12", "Quantitative Ledger & Transaction Auditor"),
        ("L13", "L13", "Reverse Engineering & Optical Illusions Specialist"),
        ("L14", "L14", "Resilient Recovery & Graceful Degradation"),
        ("L15", "L15", "Infrastructure Operations & Strict Camp Governance"),
        ("L16", "L16", "Supply Chain Logistics & Event Streaming"),
        ("L17", "L17", "Stable Infrastructure & Database Reliability"),
        ("L18", "L18", "UI/UX Designer & Client Interactions"),
        ("L19", "L19", "Adversarial Red Team & Penetration Tester"),
        ("L20", "L20", "Enterprise Monopoly Cloud Architect")
    ]
    lines.append("-- 3. Insert Learners")
    lines.append("INSERT INTO `learners` (`id`, `user_id`, `headline`) VALUES")
    learner_rows = []
    for l in learners_data:
        learner_rows.append(f"  ({escape_sql(l[0])}, {escape_sql(l[1])}, {escape_sql(l[2])})")
    lines.append(",\n".join(learner_rows) + ";\n")

    # 4. COURSES (8 courses, authored by instructors I01-I05)
    courses_data = [
        (1, "I01", "Production Database Design & High Performance MySQL 8", "production-database-design-mysql-8", "Databases", "advanced", "Master modern 3NF schema design, InnoDB buffer pools, B-Tree indexes, lock contention resolution, and transaction isolation levels for mission-critical workloads.", 89.99, "published", 70, "https://images.unsplash.com/photo-1544383835-bda2bc66a55d?w=600", "2025-10-10 10:00:00"),
        (2, "I02", "Advanced Distributed Systems & Cloud Microservices", "advanced-distributed-systems-cloud", "Cloud Architecture", "advanced", "Deconstruct the CAP theorem, distributed consensus protocols (Raft, Paxos), Kafka event fabrics, and resilience patterns under network partitions.", 99.99, "published", 75, "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=600", "2025-10-12 11:30:00"),
        (3, "I04", "Modern Full-Stack Architecture with React 19 & Python", "modern-full-stack-react-python", "Web Development", "intermediate", "Build blazing-fast modern web applications combining React 19 Client/Server components, Tailwind CSS, TanStack Query, and async Python backends.", 79.99, "published", 70, "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=600", "2025-10-14 09:00:00"),
        (4, "I03", "Applied Machine Learning & Neural Network Foundations", "applied-ml-neural-network-foundations", "Artificial Intelligence", "intermediate", "Understand backpropagation, tensor operations, CNNs, Transformers, and LLM fine-tuning workflows with PyTorch from first principles.", 94.99, "published", 70, "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=600", "2025-10-16 14:00:00"),
        (5, "I05", "Cloud Security Architecture & Zero-Trust DevSecOps", "cloud-security-zero-trust-devsecops", "Cybersecurity", "advanced", "Enterprise security posture, OAuth 2.0 / OIDC protocol deep dive, CI/CD supply chain hardening, and Kubernetes network microsegmentation.", 84.99, "published", 75, "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=600", "2025-10-18 16:30:00"),
        (6, "I04", "Mastering TypeScript & Clean Software Architecture", "mastering-typescript-clean-architecture", "Software Engineering", "intermediate", "Harness conditional types, template literals, Domain-Driven Design (DDD), hexagonal architectures, and robust contract testing.", 69.99, "published", 70, "https://images.unsplash.com/photo-1516116211227-bbc13c744be1?w=600", "2025-10-20 10:15:00"),
        (7, "I02", "Production Kubernetes & Infrastructure as Code", "production-kubernetes-iac", "DevOps", "advanced", "Declarative cloud provisioning with Terraform, multi-cluster Kubernetes networking, Ingress controllers, and production GitOps with ArgoCD.", 89.99, "published", 70, "https://images.unsplash.com/photo-1667372393119-3d4c48d07fc9?w=600", "2025-10-22 13:45:00"),
        (8, "I01", "High-Throughput Data Streaming with Kafka & Flink", "high-throughput-data-streaming-kafka-flink", "Data Engineering", "advanced", "Architect fault-tolerant stream-processing topologies, handle late-arriving events with watermarks, and integrate low-latency OLAP tables.", 94.99, "published", 70, "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600", "2025-10-25 15:00:00")
    ]
    lines.append("-- 4. Insert Courses")
    lines.append("INSERT INTO `courses` (`id`, `instructor_id`, `title`, `slug`, `category`, `difficulty`, `description`, `price`, `status`, `passing_score`, `thumbnail_url`, `created_at`) VALUES")
    course_rows = []
    for c in courses_data:
        course_rows.append(f"  ({c[0]}, {escape_sql(c[1])}, {escape_sql(c[2])}, {escape_sql(c[3])}, {escape_sql(c[4])}, {escape_sql(c[5])}, {escape_sql(c[6])}, {c[7]}, {escape_sql(c[8])}, {c[9]}, {escape_sql(c[10])}, {escape_sql(c[11])})")
    lines.append(",\n".join(course_rows) + ";\n")

    # 5. MODULES (3 modules per course = 24 modules)
    modules_data = [
        # Course 1
        (1, 1, "Advanced Relational Modeling & Normalization to 3NF", "Foundations of relational theory, Boyce-Codd Normal Form, and eliminating data anomalies.", 1),
        (2, 1, "InnoDB Internal Storage Engine & Indexing Strategies", "Deep-dive into page structures, clustered indexes, composite indexing, and execution plans.", 2),
        (3, 1, "Transaction Isolation Levels, MVCC & ACID Concurrency", "Investigating dirty reads, non-repeatable reads, phantom reads, and deadlocks in MySQL.", 3),
        # Course 2
        (4, 2, "CAP Theorem, Consistency Models & Distributed Consensus", "Theoretical boundaries of distributed systems and detailed walkthrough of Raft.", 1),
        (5, 2, "Event-Driven Microservices & Partitioned Message Queues", "Asynchronous service communication, idempotent consumers, and outbox patterns.", 2),
        (6, 2, "Distributed Tracing, Circuit Breakers & System Resilience", "OpenTelemetry instrumentation, rate limiting, and graceful degradation during outages.", 3),
        # Course 3
        (7, 3, "Modern React 19 State, Server Components & Suspense", "React 19 primitives, server actions, optimistic UI mutations, and state management.", 1),
        (8, 3, "Asynchronous Python Micro-Backends with Type Safety", "Building performant asynchronous REST APIs using FastAPI, dependency injection, and Pydantic.", 2),
        (9, 3, "Full-Stack Design Systems & Cloud Deployment", "Enterprise UI styling with Tailwind CSS, accessible component primitives, and deployment.", 3),
        # Course 4
        (10, 4, "Mathematical Foundations: Linear Algebra & Gradient Descent", "Vector spaces, matrix decomposition, automatic differentiation, and optimization functions.", 1),
        (11, 4, "Neural Architecture Design: Convolutions & Attention", "Constructing multi-layer perceptrons, self-attention mechanisms, and transformer encoders.", 2),
        (12, 4, "Production LLM Fine-Tuning & Quantization", "LoRA, QLoRA, parameter-efficient fine-tuning, and model evaluation benchmarks.", 3),
        # Course 5
        (13, 5, "Identity & Access Governance: OAuth 2.0 & OIDC", "Decentralized auth flows, JWT validation pitfalls, RBAC/ABAC models, and session security.", 1),
        (14, 5, "Supply Chain Security & Container Vulnerability Auditing", "Software Bills of Materials (SBOM), image signing with Cosign, and automated CVE gates.", 2),
        (15, 5, "Zero-Trust Network Microsegmentation & Mutual TLS", "Service mesh architecture, Istio mTLS enforcement, and defense-in-depth network policies.", 3),
        # Course 6
        (16, 6, "Advanced Type System Mastery & Generic Constraints", "Conditional types, distributive inference, branded types, and compile-time type verification.", 1),
        (17, 6, "Domain-Driven Design (DDD) & Clean Architecture Patterns", "Entities, value objects, aggregates, repositories, and decoupled business logic.", 2),
        (18, 6, "Comprehensive Automated Testing & Contract Verification", "Unit testing with Vitest, mocking strategies, and consumer-driven contract testing.", 3),
        # Course 7
        (19, 7, "Declarative Cloud Provisioning with Terraform", "HCL syntax, remote state locking, modular infrastructure, and zero-drift deployments.", 1),
        (20, 7, "Kubernetes Core Architecture & Cluster Networking", "Control plane internals, CNI plugins, Services, Ingress controllers, and DNS resolution.", 2),
        (21, 7, "GitOps Continuous Delivery Pipelines with ArgoCD", "Declarative application syncing, automated canary rollouts, and disaster recovery.", 3),
        # Course 8
        (22, 8, "Kafka Core Architecture: Partitions & Consumer Groups", "Broker internals, log replication, partition rebalancing, and exactly-once semantics.", 1),
        (23, 8, "Stateful Stream Processing with Apache Flink", "Event-time processing, tumbling/sliding windows, checkpointing, and state backends.", 2),
        (24, 8, "Low-Latency Analytics & Lakehouse Integration", "Streaming writes into ClickHouse and Apache Iceberg for real-time dashboards.", 3)
    ]
    lines.append("-- 5. Insert Modules")
    lines.append("INSERT INTO `modules` (`id`, `course_id`, `title`, `description`, `order_num`) VALUES")
    mod_rows = []
    for m in modules_data:
        mod_rows.append(f"  ({m[0]}, {m[1]}, {escape_sql(m[2])}, {escape_sql(m[3])}, {m[4]})")
    lines.append(",\n".join(mod_rows) + ";\n")

    # 6. LESSONS
    lessons_data = []
    lesson_id = 1
    lesson_topics = {
        1: [("First Normal Form (1NF) & Atomic Data Attributes", 15), ("Second Normal Form (2NF) & Functional Dependencies", 20), ("Third Normal Form (3NF) & Transitive Dependencies", 25), ("BCNF Anomalies & Real-World Normalization Tradeoffs", 30)],
        2: [("InnoDB 16KB Page Layout & Clustered Index Architecture", 25), ("Secondary B+Tree Indexes & Covering Index Optimization", 30), ("Analyzing Query Execution Plans with EXPLAIN FORMAT=JSON", 35)],
        3: [("ACID Guarantees & Two-Phase Locking (2PL)", 20), ("Read Committed vs Repeatable Read & Snapshot Isolation", 30), ("Diagnosing Lock Waits, Record Locks, and Deadlocks", 35)],
        4: [("Understanding Network Partitions & The CAP Dilemma", 20), ("Linearizability vs Sequential Consistency Explained", 25), ("Raft Consensus: Leader Election & Log Replication", 35)],
        5: [("Designing Fault-Tolerant Event Schemas with Protobuf", 20), ("The Transactional Outbox Pattern with Debezium CDC", 30), ("Consumer Rebalancing & Consumer Lag Monitoring", 25)],
        6: [("Distributed Context Propagation with OpenTelemetry", 25), ("Circuit Breaker Implementation & Fallback Patterns", 20), ("Chaos Engineering & Resiliency Validation Under Latency", 30)],
        7: [("React 19 Server Components vs Client Components Demystified", 20), ("Optimistic UI Mutations and useOptimistic Hook", 25), ("Suspense Boundaries & Streaming SSR Architecture", 30)],
        8: [("High-Performance Asynchronous Endpoints in Python", 20), ("Type Validation & Schema Serialization with Pydantic V2", 25), ("Designing Database Dependency Injections & Middleware", 25)],
        9: [("Building Accessible Component Primitives with Radix UI", 25), ("Responsive Dashboard Layouts with Modern Tailwind CSS", 20), ("End-to-End Type Safety Across Frontend and Backend", 30)],
        10: [("Linear Algebra Essentials: Vectors, Matrices, and Dot Products", 30), ("Differential Calculus & Backpropagation Algorithm", 35), ("Stochastic Gradient Descent, Momentum, and Adam Optimizer", 30)],
        11: [("Deep Convolutional Networks & Residual Connections (ResNet)", 35), ("The Scaled Dot-Product Attention Mechanism", 40), ("Encoder-Decoder Transformers vs Decoder-Only Transformers", 40)],
        12: [("Quantization Fundamentals: INT8 and FP4 Formats", 25), ("Parameter-Efficient Fine-Tuning with LoRA & QLoRA", 35), ("Evaluating LLM Hallucinations and Benchmark Reranking", 30)],
        13: [("OAuth 2.0 Authorization Code Flow with PKCE in Detail", 25), ("OpenID Connect (OIDC) Claims and Token Verification", 25), ("Designing Role-Based & Attribute-Based Access Control", 30)],
        14: [("Generating and Inspecting Software Bills of Materials (SBOM)", 20), ("Container Image Signing and Verification with Sigstore Cosign", 25), ("Automating Static Security Scans in GitHub Actions", 25)],
        15: [("Principles of Zero-Trust Network Architecture", 25), ("Enforcing Strict Mutual TLS (mTLS) with Envoy & Istio", 30), ("Container Network Interface (CNI) Network Policies", 25)],
        16: [("Generics, Constraints, and Keyof Lookups in TypeScript", 20), ("Advanced Mapped Types & Template Literal Types", 25), ("Deep Conditional Types & the `infer` Keyword in Practice", 30)],
        17: [("Deconstructing Domain Models: Entities vs Value Objects", 25), ("Designing Encapsulated Aggregates & Invariant Rules", 30), ("Hexagonal Architecture: Ports, Adapters, and Decoupled Domain", 35)],
        18: [("Writing Fast, Deterministic Unit Tests with Vitest", 20), ("Integration Testing Database Repositories with Testcontainers", 30), ("Consumer-Driven Contract Testing for Microservice APIs", 25)],
        19: [("Terraform Providers, Resources, and Remote State Locks", 25), ("Structuring Production Terraform Modules and Workspaces", 30), ("Automating Terraform Plans via Atlantis & CI/CD", 25)],
        20: [("Kubernetes Architecture: API Server, etcd, Kubelet, and Scheduler", 30), ("Pod Networking, ClusterIP, NodePort, and LoadBalancers", 30), ("Configuring Production Ingress Controllers and TLS Secrets", 35)],
        21: [("Declarative GitOps Delivery Principles with ArgoCD", 25), ("Automated Canary Deployments with Argo Rollouts", 30), ("Cluster Disaster Recovery & State Synchronization", 25)],
        22: [("Kafka Storage Engine: Commit Log Segments & Offset Tracking", 25), ("Configuring High-Throughput Producers: Acks, Batching, Lz4", 30), ("Achieving End-to-End Exactly-Once Processing in Kafka", 35)],
        23: [("Apache Flink DataStream API & Execution Graphs", 30), ("Managing Event-Time, Watermarks, and Out-of-Order Events", 35), ("Stateful Operators, Keyed State, and RocksDB StateBackend", 40)],
        24: [("Streaming Ingestion into ClickHouse MergeTree Engines", 25), ("Apache Iceberg ACID Tables on Object Storage", 30), ("Building Sub-Second Analytics Dashboards over Streaming Data", 30)]
    }

    lines.append("-- 6. Insert Lessons")
    lines.append("INSERT INTO `lessons` (`id`, `module_id`, `title`, `content_type`, `content`, `duration_minutes`, `order_num`) VALUES")
    lesson_rows = []
    for mod_id in range(1, 25):
        topics = lesson_topics[mod_id]
        for order_num, (title, duration) in enumerate(topics, 1):
            content_type = "video" if order_num % 2 == 1 else "reading"
            content = f"Comprehensive technical guide and laboratory exercise for: {title}. Covers theoretical foundations, code walkthroughs, production edge cases, and best practices."
            lesson_rows.append(f"  ({lesson_id}, {mod_id}, {escape_sql(title)}, {escape_sql(content_type)}, {escape_sql(content)}, {duration}, {order_num})")
            lessons_data.append((lesson_id, mod_id))
            lesson_id += 1
    lines.append(",\n".join(lesson_rows) + ";\n")

    # 7. QUIZZES (8 Quizzes)
    quizzes_data = [
        (1, 1, "Relational Normalization & Relational Theory Assessment", "Comprehensive assessment on 1NF, 2NF, 3NF, functional dependencies, and lossless joins.", 100, 70, 3, 25),
        (2, 4, "Distributed Consensus & Fault-Tolerance Exam", "Evaluating knowledge of Raft consensus protocol, split-brain mitigation, and consistency trade-offs.", 100, 75, 3, 30),
        (3, 7, "React 19 & Python Async Full-Stack Evaluation", "Tests core understanding of React Server Components, Suspense boundaries, and async Python event loops.", 100, 70, 3, 20),
        (4, 10, "Neural Networks & Backpropagation Foundations Quiz", "Verifies mathematical understanding of matrix calculus, gradient optimization, and tensor backprop.", 100, 70, 3, 30),
        (5, 13, "Zero-Trust Identity & Access Architecture Exam", "Assessment covering OAuth 2.0 PKCE, token verification, and defense-in-depth security principles.", 100, 75, 3, 25),
        (6, 16, "Advanced TypeScript Type Gymnastics Challenge", "Challenging assessment testing conditional types, key remap, and domain modeling constraints.", 100, 70, 3, 25),
        (7, 19, "Infrastructure as Code & Kubernetes Foundations Quiz", "Tests declarative Terraform state management, Kubernetes network policies, and pod scheduling.", 100, 70, 3, 25),
        (8, 22, "Kafka Architecture & Event Streaming Mastery Exam", "Assesses log segments, partition distribution, consumer offsets, and exactly-once semantics.", 100, 70, 3, 25)
    ]
    lines.append("-- 7. Insert Quizzes")
    lines.append("INSERT INTO `quizzes` (`id`, `module_id`, `title`, `description`, `total_marks`, `passing_marks`, `max_attempts`, `time_limit_mins`) VALUES")
    quiz_rows = []
    for q in quizzes_data:
        quiz_rows.append(f"  ({q[0]}, {q[1]}, {escape_sql(q[2])}, {escape_sql(q[3])}, {q[4]}, {q[5]}, {q[6]}, {q[7]})")
    lines.append(",\n".join(quiz_rows) + ";\n")

    # 8. QUESTIONS (40 Questions)
    questions_data = [
        # Quiz 1: Normalization
        (1, 1, "Which condition is strictly required for a relational database relation to satisfy Third Normal Form (3NF)?",
         "All multi-valued dependencies must be isolated into independent relations.",
         "It must be in 2NF and have no transitive functional dependencies of non-prime attributes on candidate keys.",
         "Every determinant must be a candidate key without exception (BCNF requirement).",
         "All columns must have unique surrogate index primary keys.", "B", 20, 1),
        (2, 1, "Under what condition is a relation in 1NF also guaranteed to be in 2NF?",
         "When all attributes are stored as variable-length VARCHAR strings.",
         "When every candidate key consists of exactly one single attribute (no composite primary keys).",
         "When the relation has foreign keys linking to at least three other tables.",
         "When null values are explicitly prohibited across every column.", "B", 20, 2),
        (3, 1, "What type of data modification anomaly occurs when removing one entity unintentionally deletes unrelated critical information?",
         "Update Anomaly", "Insertion Anomaly", "Deletion Anomaly", "Transitive Dependency Anomaly", "C", 20, 3),
        (4, 1, "In InnoDB MySQL 8, what is the default page size of a table segment?",
         "4 KB", "8 KB", "16 KB", "64 KB", "C", 20, 4),
        (5, 1, "Which B-Tree index structure directly stores the complete table row data alongside the leaf pages?",
         "Secondary Non-Clustered Index", "Clustered Primary Key Index", "Hash Index", "Spatial R-Tree Index", "B", 20, 5),

        # Quiz 2: Distributed Systems
        (6, 2, "In the Raft distributed consensus protocol, how does a candidate node become an elected Leader?",
         "By having the lowest network ping to all peer nodes.",
         "By receiving votes from a strict majority (quorum) of cluster nodes in that term.",
         "By possessing the largest disk capacity in the cluster.",
         "By transmitting a force-preemption signal to the prior leader.", "B", 20, 1),
        (7, 2, "According to the CAP Theorem, what must a distributed system sacrifice when an unavoidable network partition occurs?",
         "Network connectivity", "Storage persistence", "Either strict Consistency or complete Availability", "Throughput bandwidth", "C", 20, 2),
        (8, 2, "Which architectural pattern resolves the dual-write problem between an application database and an event broker?",
         "Saga Choreography", "Transactional Outbox Pattern with Change Data Capture (CDC)", "Circuit Breaker Pattern", "Cache-Aside Pattern", "B", 20, 3),
        (9, 2, "What occurs during a 'split-brain' condition in a distributed cluster?",
         "Nodes run out of memory simultaneously.",
         "Two disjoint subsets of nodes both believe they are the legitimate active cluster leaders.",
         "Disk sectors experience unrecoverable bit rot.",
         "A client sends contradictory RPC requests simultaneously.", "B", 20, 4),
        (10, 2, "What is the primary role of a Circuit Breaker in microservices?",
         "To encrypt all payloads in transit.",
         "To immediately fail fast and prevent cascading system collapse when a downstream dependency is failing.",
         "To automatically balance load across multiple regions.",
         "To compress JSON payloads before sending.", "B", 20, 5),

        # Quiz 3: React & Python Full Stack
        (11, 3, "What is the defining characteristic of React Server Components (RSC)?",
         "They execute solely in the browser and manipulate the virtual DOM.",
         "They execute exclusively on the server and do not add any JavaScript bundle weight to the client.",
         "They require Redux for state hydration.",
         "They only support static HTML generation without dynamic data fetching.", "B", 20, 1),
        (12, 3, "In Python's `asyncio`, what happens when a blocking CPU-heavy synchronous function is invoked without offloading?",
         "It automatically spawns a background thread.",
         "It blocks the entire event loop, preventing all concurrent asynchronous tasks from executing.",
         "It raises an immediate `RuntimeConcurrencyError`.",
         "It pauses only the current coroutine while letting others run.", "B", 20, 2),
        (13, 3, "In FastAPI, how does Pydantic V2 achieve significantly higher serialization performance compared to V1?",
         "By caching results in Redis automatically.",
         "Its core validation engine is rewritten entirely in Rust with compiled binary bindings.",
         "By skipping type validation altogether in production mode.",
         "By converting all types into raw dictionary strings.", "B", 20, 3),
        (14, 3, "What does optimistic UI updating mean in modern web interfaces?",
         "Displaying the predicted UI state immediately upon user action before server confirmation returns.",
         "Waiting for all server APIs to respond with 200 OK before rendering anything.",
         "Using optimistic lock versioning in database tables.",
         "Ignoring network error alerts in the browser console.", "A", 20, 4),
        (15, 3, "Which HTTP header is essential for enabling Server-Sent Events (SSE) streaming?",
         "Content-Type: application/json", "Content-Type: text/event-stream", "Accept: text/html", "Transfer-Encoding: chunked-gzip", "B", 20, 5),

        # Quiz 4: ML Foundations
        (16, 4, "What does the chain rule enable in artificial neural networks?",
         "Sequential data loading from disk into RAM.",
         "Exact recursive computation of gradients through nested layers during backpropagation.",
         "Random initialization of weights according to Gaussian distributions.",
         "Lossless compression of activation vectors.", "B", 20, 1),
        (17, 4, "Why does the vanishing gradient problem occur with standard sigmoid activation functions in deep networks?",
         "Because the derivative of the sigmoid saturates and peaks at only 0.25, shrinking gradients exponentially through layers.",
         "Because sigmoid functions produce infinite outputs when inputs approach zero.",
         "Because weights are multiplied by negative infinity.",
         "Because GPUs cannot compute transcendental exponential curves.", "A", 20, 2),
        (18, 4, "What is the computational complexity of standard self-attention relative to sequence length N?",
         "O(N)", "O(N log N)", "O(N^2)", "O(2^N)", "C", 20, 3),
        (19, 4, "In Low-Rank Adaptation (LoRA), how are fine-tuning parameters kept minimal?",
         "By discarding 90% of model layers entirely.",
         "By freezing original weights and decomposing weight update matrices into products of two low-rank matrices A and B.",
         "By quantizing all float32 weights into 1-bit booleans.",
         "By training only the final single output classification token.", "B", 20, 4),
        (20, 4, "Which optimizer maintains running exponential moving averages of both the gradients and the squared gradients?",
         "Stochastic Gradient Descent (SGD)", "Adagrad", "Adam", "Momentum SGD", "C", 20, 5),

        # Quiz 5: Zero Trust Cloud Security
        (21, 5, "What security vulnerability does Proof Key for Code Exchange (PKCE) mitigate in OAuth 2.0?",
         "SQL injection attacks in user authentication portals.",
         "Authorization code interception attacks on public clients lacking client secrets.",
         "Cross-Site Request Forgery (CSRF) on static web servers.",
         "Denial of Service attacks against identity provider token endpoints.", "B", 20, 1),
        (22, 5, "What is the core philosophical tenet of a Zero-Trust security architecture?",
         "Trust all internal network traffic inside the perimeter firewall.",
         "Never trust, always verify every request regardless of source or network perimeter.",
         "Trust requests signed by corporate VPN IP addresses.",
         "Rely solely on complex user password policies.", "B", 20, 2),
        (23, 5, "In Mutual TLS (mTLS), what cryptographic validation occurs that differs from standard TLS?",
         "Data is encrypted twice with different algorithms.",
         "Both the server AND the client present and authenticate cryptographic x509 certificates to each other.",
         "The client decrypts server keys without certificate authority verification.",
         "Network routers inspect encrypted packet bodies in transit.", "B", 20, 3),
        (24, 5, "What is a Software Bill of Materials (SBOM) used for in secure DevSecOps pipelines?",
         "Tracking cloud infrastructure monthly billing expenses.",
         "Providing a comprehensive, verifiable machine-readable manifest of all third-party software components and dependencies.",
         "Calculating developer code review throughput.",
         "Generating automated API documentation for web clients.", "B", 20, 4),
        (25, 5, "Why is asymmetric JWT signature verification (e.g. RS256/ES256) preferred over symmetric (HS256) in microservice architectures?",
         "Because HS256 requires sharing the secret signing key with every consuming microservice to verify tokens.",
         "Because RS256 produces much smaller token strings than HS256.",
         "Because HS256 cannot contain user role claims.",
         "Because asymmetric algorithms use no mathematical keys.", "A", 20, 5),

        # Quiz 6: TypeScript Mastery
        (26, 6, "What does the `never` type represent in TypeScript?",
         "A value that can be null or undefined.",
         "A type representing values that never occur, such as a function that always throws or unreachable code branches.",
         "An alias for `any` without type safety warnings.",
         "A type that can be dynamically converted to any primitive at runtime.", "B", 20, 1),
        (27, 6, "How do distributive conditional types behave in TypeScript when applied to a naked type parameter over a union?",
         "They throw a compilation error immediately.",
         "They distribute automatically over each constituent member of the union type.",
         "They collapse the union into the first type in the union list.",
         "They coerce the entire union into `unknown`.", "B", 20, 2),
        (28, 6, "In Domain-Driven Design (DDD), what distinguishes an Entity from a Value Object?",
         "An Entity has a distinct identity that persists over time, whereas a Value Object is defined solely by its attribute values.",
         "Entities can be persisted in MySQL, but Value Objects can only exist in Redis.",
         "Value Objects have mutable state, while Entities are strictly frozen.",
         "Entities cannot contain business logic methods.", "A", 20, 3),
        (29, 6, "What is the primary benefit of 'Branded Types' (Nominal Typing) in TypeScript?",
         "Accelerating TypeScript compilation times by 50%.",
         "Preventing accidental substitution of structurally identical primitives (e.g., UserId vs OrderId).",
         "Exporting types directly to JavaScript source code.",
         "Automatically creating database tables from interfaces.", "B", 20, 4),
        (30, 6, "What does the `infer` keyword allow inside conditional TypeScript types?",
         "Declaring runtime JavaScript variables.",
         "Introducing a type variable to be deduced from the type being examined in the conditional check.",
         "Forcing the compiler to bypass strict null checking.",
         "Importing types dynamically from external packages.", "B", 20, 5),

        # Quiz 7: Kubernetes & DevOps
        (31, 7, "In Kubernetes, which component acts as the single source of truth and distributed key-value store for cluster state?",
         "kube-proxy", "etcd", "kubelet", "CoreDNS", "B", 20, 1),
        (32, 7, "What is the primary purpose of Terraform Remote State with state locking?",
         "To encrypt source code on GitHub.",
         "To prevent concurrent team members from executing overlapping writes and corrupting infrastructure state.",
         "To compress Docker images before deploying to clusters.",
         "To restart cloud virtual machines on reboot.", "B", 20, 2),
        (33, 7, "What does a Kubernetes Horizontal Pod Autoscaler (HPA) do?",
         "Scales the physical node memory of the server.",
         "Automatically adjusts the number of pod replicas based on observed CPU utilization or custom metrics.",
         "Migrates pods across geographic regions during power failures.",
         "Compresses persistent volumes when disk space falls below 10%.", "B", 20, 3),
        (34, 7, "In GitOps (e.g. ArgoCD), what is considered the single authoritative source of truth for desired cluster state?",
         "The live Kubernetes etcd cluster state.",
         "A Git repository containing declarative manifests or Helm charts.",
         "The local developer machine's terminal history.",
         "The cloud provider's web console dashboard.", "B", 20, 4),
        (35, 7, "What is the function of a Kubernetes Ingress Controller?",
         "Routing external HTTP/S traffic to internal cluster Services based on hostnames and URL paths.",
         "Encrypting container images stored in private registries.",
         "Managing physical cables in on-premise server racks.",
         "Compiling Go source code into container binaries.", "A", 20, 5),

        # Quiz 8: Kafka Streaming
        (36, 8, "How does Apache Kafka achieve horizontal scalability across consumers?",
         "By duplicating every message to all consumers worldwide.",
         "By partitioning topics and assigning individual partitions to specific consumers within a Consumer Group.",
         "By compressing messages into zip files on disk.",
         "By running all consumers on a single CPU core.", "B", 20, 1),
        (37, 8, "What does the `acks=all` setting on an Apache Kafka producer guarantee?",
         "The message is stored in memory on the client machine.",
         "The message is acknowledged only after all in-sync replicas (ISRs) have successfully committed it to their local logs.",
         "Every consumer on the internet has read the message.",
         "The message will never expire from the topic regardless of retention policies.", "B", 20, 2),
        (38, 8, "In stream processing (Apache Flink), what is a 'Watermark'?",
         "A metric tracking network bandwidth saturation.",
         "A timestamp marker embedded in the stream declaring that no records with an earlier event-time will arrive.",
         "A cryptographic hash proving packet provenance.",
         "A memory buffer cleanup trigger.", "B", 20, 3),
        (39, 8, "What is the primary distinction between Tumbling Windows and Sliding Windows in stream analytics?",
         "Tumbling windows are non-overlapping fixed intervals, while sliding windows can overlap with specified slide frequencies.",
         "Tumbling windows operate on disk, while sliding windows operate in RAM.",
         "Tumbling windows cannot calculate aggregations.",
         "Sliding windows drop late-arriving events automatically.", "A", 20, 4),
        (40, 8, "Why are append-only commit logs exceptionally fast for disk I/O in Kafka?",
         "Because sequential disk writes utilize OS page cache optimizations and avoid random seek head penalties.",
         "Because disks do not need electrical power during append operations.",
         "Because append operations bypass the operating system kernel entirely.",
         "Because append logs delete previous data to save storage.", "A", 20, 5)
    ]
    lines.append("-- 8. Insert Questions")
    lines.append("INSERT INTO `questions` (`id`, `quiz_id`, `question_text`, `option_a`, `option_b`, `option_c`, `option_d`, `correct_option`, `marks`, `order_num`) VALUES")
    q_rows = []
    for q in questions_data:
        q_rows.append(f"  ({q[0]}, {q[1]}, {escape_sql(q[2])}, {escape_sql(q[3])}, {escape_sql(q[4])}, {escape_sql(q[5])}, {escape_sql(q[6])}, {escape_sql(q[7])}, {q[8]}, {q[9]})")
    lines.append(",\n".join(q_rows) + ";\n")

    # 9. ENROLMENTS (35 enrolments, learner_id L01-L20)
    raw_enrolments = [
        # Completed (IDs 1-11)
        (1, 1, 1, 'completed', 100.00, '2025-10-20 14:00:00', '2025-11-28 17:30:00', None),
        (2, 2, 2, 'completed', 100.00, '2025-10-25 10:15:00', '2025-12-05 16:45:00', None),
        (3, 3, 1, 'completed', 100.00, '2025-11-01 09:30:00', '2025-12-15 11:20:00', None),
        (4, 4, 2, 'completed', 100.00, '2025-11-05 13:45:00', '2026-01-10 18:00:00', None),
        (5, 5, 3, 'completed', 100.00, '2025-11-12 11:00:00', '2026-01-20 14:15:00', None),
        (6, 6, 4, 'completed', 100.00, '2025-11-20 15:20:00', '2026-02-05 16:30:00', None),
        (7, 7, 3, 'completed', 100.00, '2025-12-01 10:00:00', '2026-02-18 12:45:00', None),
        (8, 8, 5, 'completed', 100.00, '2025-12-10 14:30:00', '2026-03-01 17:10:00', None),
        (9, 9, 7, 'completed', 100.00, '2025-12-15 08:45:00', '2026-03-15 15:25:00', None),
        (10, 10, 6, 'completed', 100.00, '2026-01-05 11:30:00', '2026-04-02 14:00:00', None),
        (11, 11, 8, 'completed', 100.00, '2026-01-12 16:00:00', '2026-04-20 18:30:00', None),

        # Active (IDs 12-28)
        (12, 1, 3, 'active', 63.64, '2026-02-01 10:00:00', None, None),
        (13, 2, 7, 'active', 72.73, '2026-02-10 14:20:00', None, None),
        (14, 3, 4, 'active', 54.55, '2026-02-15 11:30:00', None, None),
        (15, 4, 8, 'active', 81.82, '2026-03-01 09:15:00', None, None),
        (16, 5, 6, 'active', 45.45, '2026-03-10 15:40:00', None, None),
        (17, 6, 8, 'active', 63.64, '2026-03-18 13:00:00', None, None),
        (18, 7, 6, 'active', 36.36, '2026-04-01 11:10:00', None, None),
        (19, 8, 7, 'active', 81.82, '2026-04-12 16:30:00', None, None),
        (20, 9, 2, 'active', 54.55, '2026-04-25 10:45:00', None, None),
        (21, 10, 5, 'active', 45.45, '2026-05-05 14:00:00', None, None),
        (22, 12, 1, 'active', 72.73, '2026-05-18 09:30:00', None, None),
        (23, 13, 3, 'active', 27.27, '2026-06-01 11:15:00', None, None),
        (24, 14, 5, 'active', 63.64, '2026-06-15 15:50:00', None, None),
        (25, 15, 4, 'active', 81.82, '2026-07-02 10:20:00', None, None),
        (26, 16, 1, 'active', 36.36, '2026-07-20 14:40:00', None, None),
        (27, 17, 3, 'active', 18.18, '2026-08-10 16:15:00', None, None),
        (28, 18, 2, 'active', 27.27, '2026-09-01 11:00:00', None, None),

        # Dropped (IDs 29-35)
        (29, 13, 2, 'dropped', 9.09, '2025-11-15 09:00:00', None, '2025-12-20 10:30:00'),
        (30, 14, 1, 'dropped', 18.18, '2025-12-05 14:00:00', None, '2026-01-18 11:45:00'),
        (31, 15, 6, 'dropped', 9.09, '2026-01-10 10:30:00', None, '2026-02-15 16:20:00'),
        (32, 16, 7, 'dropped', 9.09, '2026-02-01 15:15:00', None, '2026-03-10 09:50:00'),
        (33, 17, 8, 'dropped', 18.18, '2026-03-05 11:00:00', None, '2026-04-12 14:30:00'),
        (34, 19, 5, 'dropped', 9.09, '2026-04-01 13:40:00', None, '2026-05-15 10:15:00'),
        (35, 20, 3, 'dropped', 18.18, '2026-05-10 16:20:00', None, '2026-06-25 12:00:00')
    ]

    enrolments_data = []
    for en in raw_enrolments:
        lrn_id = f"L{en[1]:02d}"
        enrolments_data.append((en[0], lrn_id, en[2], en[3], en[4], en[5], en[6], en[7]))

    lines.append("-- 9. Insert Enrolments")
    lines.append("INSERT INTO `enrolments` (`id`, `learner_id`, `course_id`, `status`, `progress`, `enrolled_at`, `completed_at`, `dropped_at`) VALUES")
    enr_rows = []
    for e in enrolments_data:
        enr_rows.append(f"  ({e[0]}, {escape_sql(e[1])}, {e[2]}, {escape_sql(e[3])}, {e[4]}, {escape_sql(e[5])}, {escape_sql(e[6])}, {escape_sql(e[7])})")
    lines.append(",\n".join(enr_rows) + ";\n")

    # 10. LESSON PROGRESS
    course_lessons = {}
    for mod_id in range(1, 25):
        c_id = (mod_id - 1) // 3 + 1
        if c_id not in course_lessons:
            course_lessons[c_id] = []
        for l_id, m_id in lessons_data:
            if m_id == mod_id:
                course_lessons[c_id].append(l_id)

    lines.append("-- 10. Insert Lesson Progress")
    lines.append("INSERT INTO `lesson_progress` (`enrolment_id`, `lesson_id`, `is_completed`, `completed_at`, `last_accessed_at`) VALUES")
    lp_rows = []
    for enr in enrolments_data:
        enr_id = enr[0]
        c_id = enr[2]
        status = enr[3]
        progress_pct = enr[4]
        enrolled_time = enr[5]
        completed_time = enr[6]
        c_les = course_lessons[c_id]
        total_in_c = len(c_les)

        if status == 'completed':
            num_completed = total_in_c
        else:
            num_completed = int(round((progress_pct / 100.0) * total_in_c))

        for idx, les_id in enumerate(c_les):
            is_done = (idx < num_completed)
            c_date = completed_time if (is_done and completed_time) else (enrolled_time if is_done else None)
            access_date = completed_time if completed_time else enrolled_time
            lp_rows.append(f"  ({enr_id}, {les_id}, {1 if is_done else 0}, {escape_sql(c_date)}, {escape_sql(access_date)})")
    lines.append(",\n".join(lp_rows) + ";\n")

    # 11. ATTEMPTS (45 attempts, learner_id L01-L20)
    raw_attempts = [
        # Completed learners (pass attempt)
        (1, 1, 1, 1, 100.00, 100.00, 1, '2025-11-20 15:00:00', '2025-11-20 15:22:00'),
        (2, 2, 2, 1, 80.00, 100.00, 1, '2025-11-28 11:00:00', '2025-11-28 11:25:00'),
        (3, 1, 3, 1, 60.00, 100.00, 0, '2025-11-30 09:00:00', '2025-11-30 09:20:00'),
        (4, 1, 3, 2, 100.00, 100.00, 1, '2025-12-05 14:00:00', '2025-12-05 14:18:00'),
        (5, 2, 4, 1, 100.00, 100.00, 1, '2025-12-28 16:30:00', '2025-12-28 16:55:00'),
        (6, 3, 5, 1, 80.00, 100.00, 1, '2026-01-15 10:15:00', '2026-01-15 10:32:00'),
        (7, 4, 6, 1, 100.00, 100.00, 1, '2026-01-30 14:00:00', '2026-01-30 14:26:00'),
        (8, 3, 7, 1, 100.00, 100.00, 1, '2026-02-12 11:00:00', '2026-02-12 11:19:00'),
        (9, 5, 8, 1, 80.00, 100.00, 1, '2026-02-24 15:45:00', '2026-02-24 16:10:00'),
        (10, 7, 9, 1, 100.00, 100.00, 1, '2026-03-08 13:30:00', '2026-03-08 13:52:00'),
        (11, 6, 10, 1, 80.00, 100.00, 1, '2026-03-25 10:00:00', '2026-03-25 10:24:00'),
        (12, 8, 11, 1, 100.00, 100.00, 1, '2026-04-14 16:00:00', '2026-04-14 16:23:00'),

        # Active learners attempts
        (13, 3, 1, 1, 60.00, 100.00, 0, '2026-02-20 14:00:00', '2026-02-20 14:25:00'),
        (14, 3, 1, 2, 80.00, 100.00, 1, '2026-03-02 11:30:00', '2026-03-02 11:50:00'),
        (15, 7, 2, 1, 80.00, 100.00, 1, '2026-03-10 16:00:00', '2026-03-10 16:25:00'),
        (16, 4, 3, 1, 40.00, 100.00, 0, '2026-03-12 09:30:00', '2026-03-12 09:55:00'),
        (17, 4, 3, 2, 60.00, 100.00, 0, '2026-03-22 15:00:00', '2026-03-22 15:24:00'),
        (18, 8, 4, 1, 80.00, 100.00, 1, '2026-03-28 10:15:00', '2026-03-28 10:40:00'),
        (19, 6, 5, 1, 60.00, 100.00, 0, '2026-04-05 14:20:00', '2026-04-05 14:45:00'),
        (20, 8, 6, 1, 80.00, 100.00, 1, '2026-04-15 11:00:00', '2026-04-15 11:22:00'),
        (21, 7, 8, 1, 100.00, 100.00, 1, '2026-04-20 15:30:00', '2026-04-20 15:52:00'),
        (22, 2, 9, 1, 60.00, 100.00, 0, '2026-05-02 09:00:00', '2026-05-02 09:25:00'),
        (23, 2, 9, 2, 80.00, 100.00, 1, '2026-05-14 14:00:00', '2026-05-14 14:23:00'),
        (24, 5, 10, 1, 60.00, 100.00, 0, '2026-05-20 11:00:00', '2026-05-20 11:25:00'),
        (25, 1, 12, 1, 80.00, 100.00, 1, '2026-06-05 10:30:00', '2026-06-05 10:52:00'),
        (26, 5, 14, 1, 80.00, 100.00, 1, '2026-06-25 15:00:00', '2026-06-25 15:23:00'),
        (27, 4, 15, 1, 100.00, 100.00, 1, '2026-07-15 11:15:00', '2026-07-15 11:38:00'),
        (28, 1, 16, 1, 40.00, 100.00, 0, '2026-08-01 14:00:00', '2026-08-01 14:22:00'),
        (29, 3, 17, 1, 20.00, 100.00, 0, '2026-08-20 09:30:00', '2026-08-20 09:50:00'),
        (30, 2, 18, 1, 40.00, 100.00, 0, '2026-09-10 16:00:00', '2026-09-10 16:25:00'),

        # Dropped learners attempts
        (31, 2, 13, 1, 40.00, 100.00, 0, '2025-12-01 10:00:00', '2025-12-01 10:22:00'),
        (32, 1, 14, 1, 40.00, 100.00, 0, '2025-12-20 14:30:00', '2025-12-20 14:50:00'),
        (33, 6, 15, 1, 20.00, 100.00, 0, '2026-01-25 11:00:00', '2026-01-25 11:18:00'),
        (34, 7, 16, 1, 40.00, 100.00, 0, '2026-02-18 15:00:00', '2026-02-18 15:22:00'),
        (35, 8, 17, 1, 40.00, 100.00, 0, '2026-03-20 10:30:00', '2026-03-20 10:52:00'),
        (36, 5, 19, 1, 20.00, 100.00, 0, '2026-04-20 14:00:00', '2026-04-20 14:20:00'),
        (37, 3, 20, 1, 40.00, 100.00, 0, '2026-05-25 11:30:00', '2026-05-25 11:50:00'),

        # Additional attempts to enrich statistics
        (38, 1, 2, 1, 100.00, 100.00, 1, '2026-01-10 10:00:00', '2026-01-10 10:20:00'),
        (39, 2, 1, 1, 100.00, 100.00, 1, '2026-01-12 15:30:00', '2026-01-12 15:52:00'),
        (40, 3, 2, 1, 80.00, 100.00, 1, '2026-02-05 11:00:00', '2026-02-05 11:22:00'),
        (41, 4, 1, 1, 80.00, 100.00, 1, '2026-02-18 14:00:00', '2026-02-18 14:24:00'),
        (42, 5, 2, 1, 80.00, 100.00, 1, '2026-03-01 09:30:00', '2026-03-01 09:55:00'),
        (43, 6, 1, 1, 100.00, 100.00, 1, '2026-03-15 16:00:00', '2026-03-15 16:21:00'),
        (44, 7, 1, 1, 80.00, 100.00, 1, '2026-04-02 11:15:00', '2026-04-02 11:36:00'),
        (45, 8, 2, 1, 100.00, 100.00, 1, '2026-04-22 14:45:00', '2026-04-22 15:08:00')
    ]

    attempts_data = []
    for att in raw_attempts:
        lrn_id = f"L{att[2]:02d}"
        attempts_data.append((att[0], att[1], lrn_id, att[3], att[4], att[5], att[6], att[7], att[8]))

    lines.append("-- 11. Insert Attempts")
    lines.append("INSERT INTO `attempts` (`id`, `quiz_id`, `learner_id`, `attempt_number`, `score`, `total_marks`, `is_passed`, `started_at`, `submitted_at`) VALUES")
    att_rows = []
    for a in attempts_data:
        att_rows.append(f"  ({a[0]}, {a[1]}, {escape_sql(a[2])}, {a[3]}, {a[4]}, {a[5]}, {a[6]}, {escape_sql(a[7])}, {escape_sql(a[8])})")
    lines.append(",\n".join(att_rows) + ";\n")

    # 12. RESPONSES
    correct_lookup = {q[0]: q[7] for q in questions_data}
    lines.append("-- 12. Insert Question Responses")
    lines.append("INSERT INTO `responses` (`attempt_id`, `question_id`, `chosen_option`, `is_correct`, `marks_obtained`) VALUES")
    resp_rows = []
    for att in attempts_data:
        att_id = att[0]
        q_id = att[1]
        score = att[4]
        num_correct = int(round(score / 20.0))
        quiz_q_ids = [q_id * 5 - 4 + offset for offset in range(5)]

        for i, q_num in enumerate(quiz_q_ids):
            correct_opt = correct_lookup[q_num]
            if i < num_correct:
                chosen = correct_opt
                is_correct = 1
                marks = 20.00
            else:
                options = ["A", "B", "C", "D"]
                options.remove(correct_opt)
                chosen = options[0]
                is_correct = 0
                marks = 0.00
            resp_rows.append(f"  ({att_id}, {q_num}, {escape_sql(chosen)}, {is_correct}, {marks})")
    lines.append(",\n".join(resp_rows) + ";\n")

    # 13. CERTIFICATES (11 certificates for completed enrolments 1-11)
    certificates_data = [
        (1, 1, "LP-2025-A9E4-71F2", "2025-11-28 17:35:00", "/verify/LP-2025-A9E4-71F2"),
        (2, 2, "LP-2025-B4C1-88D3", "2025-12-05 16:50:00", "/verify/LP-2025-B4C1-88D3"),
        (3, 3, "LP-2025-C7D8-99A1", "2025-12-15 11:25:00", "/verify/LP-2025-C7D8-99A1"),
        (4, 4, "LP-2026-D1F2-44E5", "2026-01-10 18:05:00", "/verify/LP-2026-D1F2-44E5"),
        (5, 5, "LP-2026-E3B9-22A7", "2026-01-20 14:20:00", "/verify/LP-2026-E3B9-22A7"),
        (6, 6, "LP-2026-F5A6-33D8", "2026-02-05 16:35:00", "/verify/LP-2026-F5A6-33D8"),
        (7, 7, "LP-2026-A2E8-77C1", "2026-02-18 12:50:00", "/verify/LP-2026-A2E8-77C1"),
        (8, 8, "LP-2026-B8C3-55F4", "2026-03-01 17:15:00", "/verify/LP-2026-B8C3-55F4"),
        (9, 9, "LP-2026-C4D9-66E2", "2026-03-15 15:30:00", "/verify/LP-2026-C4D9-66E2"),
        (10, 10, "LP-2026-D9F1-88B3", "2026-04-02 14:05:00", "/verify/LP-2026-D9F1-88B3"),
        (11, 11, "LP-2026-E7A4-99C5", "2026-04-20 18:35:00", "/verify/LP-2026-E7A4-99C5")
    ]
    lines.append("-- 13. Insert Certificates")
    lines.append("INSERT INTO `certificates` (`id`, `enrolment_id`, `certificate_code`, `issued_at`, `certificate_url`) VALUES")
    cert_rows = []
    for cert in certificates_data:
        cert_rows.append(f"  ({cert[0]}, {cert[1]}, {escape_sql(cert[2])}, {escape_sql(cert[3])}, {escape_sql(cert[4])})")
    lines.append(",\n".join(cert_rows) + ";\n")

    # 14. FEEDBACK (18 reviews, realistic testimonials referencing RDR2 gang instructors)
    feedback_data = [
        (1, 1, 5, "Invaluable for Production Database Engineers", "Hosea Matthews demystified InnoDB clustered page structures and transaction isolation. Resolved two critical deadlock bugs in our settlement ledger immediately after applying this course.", "2025-11-29 09:15:00"),
        (2, 2, 5, "World-Class Distributed Systems Course", "Arthur Morgan's Raft consensus breakdowns and failure-domain analysis are top-tier. Essential curriculum for anyone building resilient frontier infrastructure.", "2025-12-06 14:20:00"),
        (3, 3, 5, "Best 3NF & SQL Performance Training", "Clear, rigorous, and directly applicable. The index coverage and EXPLAIN queries transformed our slow analytics queries.", "2025-12-16 10:30:00"),
        (4, 4, 4, "Deep Dive into Modern Microservices", "Extremely solid breakdown of the outbox pattern and Kafka idempotency. Arthur's real-world stories from the frontier make complex engineering intuitive.", "2026-01-11 16:45:00"),
        (5, 5, 5, "Superb React 19 & Python Async Integration", "Charles Smith's architectural design patterns are immaculate. The end-to-end type safety between FastAPI and React 19 Server Actions is executed flawlessly.", "2026-01-21 11:10:00"),
        (6, 6, 5, "Mathematical Clarity in Deep Learning", "Sadie Adler explains backpropagation and transformer attention with sharp precision. The PyTorch laboratories are immaculate.", "2026-02-06 17:00:00"),
        (7, 7, 5, "Unmatched UI Architecture & State Management", "Building optimistic UI and resilient design systems was exactly what my team needed. Charles is a legendary instructor.", "2026-02-19 13:40:00"),
        (8, 8, 4, "Rigorous Zero-Trust & Cloud Security", "PKCE flows and mTLS enforcement were explained thoroughly. John Marston bridges the gap between rugged survival and practical engineering.", "2026-03-02 10:25:00"),
        (9, 9, 5, "Mastery of Production Kubernetes & GitOps", "Arthur Morgan's canary deployments and Helm chart structure are production-ready. Adopted directly into our staging clusters.", "2026-03-16 12:15:00"),
        (10, 10, 5, "TypeScript Type Gymnastics Masterclass", "Conditional type inference and domain-driven aggregates were mind-expanding. Truly elevated software craftsmanship across our gang's code.", "2026-04-03 15:50:00"),
        (11, 11, 5, "Exceptional Kafka & Flink Streaming Topologies", "Watermarks, sliding windows, and exactly-once semantics explained clearly with zero fluff by Hosea. Top tier material.", "2026-04-21 09:40:00"),
        (12, 12, 4, "High Quality Content in Mid-Course", "Currently halfway through Course 3. The React 19 server primitives are well demonstrated. Looking forward to completing the final module.", "2026-04-10 18:20:00"),
        (13, 13, 5, "Great Terraform & Kubernetes Insights", "The remote state locking and multi-cluster CNI configurations are spot on. Already 70% completed.", "2026-04-18 11:30:00"),
        (14, 15, 4, "Great Stream Processing Foundations", "Loving the Flink state backend walkthroughs. Highly educational.", "2026-05-02 14:15:00"),
        (15, 19, 5, "Top-Notch DevOps & Infrastructure", "Hands down the best practical container networking course available.", "2026-05-15 16:50:00"),
        (16, 22, 5, "Deep Dive into MySQL Query Execution", "The InnoDB buffer pool and locking analysis by Hosea is unmatched anywhere.", "2026-06-10 10:00:00"),
        (17, 24, 4, "Practical Security Engineering", "Very good security architecture practices by Sadie Adler. Helped our SOC team tremendously.", "2026-07-05 13:30:00"),
        (18, 25, 5, "Flawless Machine Learning Foundations", "Intuitive explanations of vector spaces and gradient descent optimization.", "2026-07-28 15:10:00")
    ]
    lines.append("-- 14. Insert Feedback")
    lines.append("INSERT INTO `feedback` (`id`, `enrolment_id`, `rating`, `review_title`, `comments`, `created_at`) VALUES")
    fb_rows = []
    for fb in feedback_data:
        fb_rows.append(f"  ({fb[0]}, {fb[1]}, {fb[2]}, {escape_sql(fb[3])}, {escape_sql(fb[4])}, {escape_sql(fb[5])})")
    lines.append(",\n".join(fb_rows) + ";\n")

    return "\n".join(lines)

if __name__ == "__main__":
    sql_text = generate_seed_sql()
    with open("sql/seed.sql", "w", encoding="utf-8") as f:
        f.write(sql_text)
    print(f"Successfully generated sql/seed.sql ({len(sql_text.splitlines())} lines)")
