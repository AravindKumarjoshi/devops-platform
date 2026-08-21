# 📘 Data & Configuration Serialization — Comprehensive Cheat Sheet

## 📑 Table of Contents
- [1. Data Serialization Architecture & Format Comparison Matrix](#1-data-serialization-architecture--format-comparison-matrix)
- [2. YAML Mastery (Kubernetes, CI/CD & Ansible Standard)](#2-yaml-mastery-kubernetes-cicd--ansible-standard)
- [3. JSON & JSON Schema Mastery (REST APIs & Cloud Architecture)](#3-json--json-schema-mastery-rest-apis--cloud-architecture)
- [4. TOML Mastery (Modern Python Packaging & Rust Configurations)](#4-toml-mastery-modern-python-packaging--rust-configurations)
- [5. XML & XPath Mastery (Legacy Enterprise Systems, Maven & SOAP)](#5-xml--xpath-mastery-legacy-enterprise-systems-maven--soap)
- [6. HashiCorp Configuration Language (HCL — Terraform & OpenTofu)](#6-hashicorp-configuration-language-hcl--terraform--opentofu)
- [7. INI & Legacy Flat Property Formats](#7-ini--legacy-flat-property-formats)
- [8. CLI Conversion & Pipeline Processing Cheat Sheet](#8-cli-conversion--pipeline-processing-cheat-sheet)

---

## 1. Data Serialization Architecture & Format Comparison Matrix

**🌐 Analogy:** Diplomatic Language Translation at the UN. Human runtime objects in memory (Python dictionaries, Go structs, Java POJOs) must be written down on standardized diplomatic treaty papers (serialization formats) so foreign software systems across the globe can ingest and reconstruct them without misunderstanding a single comma!

### What is it? (What & Why)
Serialization is the process of translating data structures or object states into a format that can be stored (for example, in a file or memory buffer) or transmitted (across a network connection) and reconstructed later (deserialization). Without standard serialization formats, systems running different programming languages on different operating systems would not be able to communicate structured data. 

### How it Works & Diagram

```mermaid
graph LR
    subgraph "Sender (Go / Python / Java)"
        A["Runtime Memory Objects"] -->|Serializer Encoder| B["Serialization Format (JSON/YAML/etc.)"]
    end
    
    B -->|Wire Network Payload / Disk File| C{"Transport/Storage"}
    
    C --> B2["Serialization Format (JSON/YAML/etc.)"]
    
    subgraph "Receiver (Rust / JS / C++)"
        B2 -->|Deserializer Parser| D["Receiver Memory Objects"]
    end
```

### An Exhaustive Comparison Table

| Feature | JSON | YAML | TOML | XML | HCL | INI |
|---|---|---|---|---|---|---|
| **Primary Use Case** | APIs, Data Interchange | CI/CD, K8s, Ansible | App Configs, Packaging | Legacy, SOAP, Java | IaC (Terraform) | Simple Configs |
| **Readability** | Good (Machine-focused) | Excellent (Human-focused) | Excellent | Poor (Verbose) | Excellent | Excellent |
| **Comments** | ❌ No | ✅ Yes (`#`) | ✅ Yes (`#`) | ✅ Yes (`<!-- -->`) | ✅ Yes (`#`, `//`, `/* */`) | ✅ Yes (`#`, `;`) |
| **Hierarchy** | Braces & Brackets | Whitespace Indentation | Dot notation / Brackets | Nested Tags | Block structures | Flat (Sections) |
| **Data Types** | String, Num, Bool, Null, Arr, Obj | Rich (Dates, Binary, etc.) | Strong (Dates, Time, etc.) | String (Needs XSD) | String, Num, Bool, List, Map | String only |
| **Parsing Speed** | 🚀 Extremely Fast | 🐢 Slow | 🚗 Fast | 🚜 Slow | 🚗 Fast | 🚀 Fast |

---

## 2. YAML Mastery (Kubernetes, CI/CD & Ansible Standard)

**🌐 Analogy:** A Japanese Zen Garden. Everything relies entirely on clean whitespace and strict spatial harmony; one out-of-place rake pebble (an errant Tab character!) destroys the harmony of the entire garden and crashes the parser!

### What is it? (What & Why)
YAML (YAML Ain't Markup Language) is a human-friendly data serialization standard. Its design goals emphasize readability and ease of use for configuration files. It is the de facto standard for infrastructure as code, CI/CD pipelines (GitHub Actions, GitLab CI), and Kubernetes manifests.

### Structure & How to Write It (Beginner to Advanced)

- **Key-Value Pairs & Sequences:** Uses colons `:` for mappings and hyphens `-` for sequence lists.
- **Indentation:** Exactly spaces (usually 2). Tabs are strictly forbidden.
- **Block Scalars:** 
  - Literal `|` retains newlines.
  - Folded `>` converts newlines into spaces (folding them).
- **Advanced Features:** 
  - **Anchors (`&label`)** to define a chunk of configuration.
  - **Aliases (`*label`)** to reference that chunk.
  - **Merge Keys (`<<: *label`)** to merge the anchored dictionary into the current one, allowing for DRY configs.
  - **Multi-document streams:** Separated by `---`.

```mermaid
graph TD
    A["YAML Document"] --> B["Scalars (String, Int, Bool)"]
    A --> C["Collections"]
    C --> D["Mappings (Dictionaries: key: value)"]
    C --> E["Sequences (Lists: - item)"]
    A --> F["Directives (---, ...)"]
```

### 🛠️ Beginner-to-Advanced Syntax & Data Modeling Guide (How to Use It)

- **Scalars & Data Types:**
  - **Strings:** Can be written bare `hello`, in single quotes `'hello world'` (to prevent parsing special characters), or double quotes `"hello\nworld"` (to process escape sequences).
  - **Integers & Floats:** `count: 42`, `pi: 3.14`
  - **Booleans:** `true`, `false`, `yes`, `no` (Note: YAML 1.2 removed `yes`/`no`, but YAML 1.1 used by many parsers still supports them).
  - **Null values:** `null` or `~`
- **Lists / Sequences (Arrays):**
  Standard block syntax uses hyphens:
  ```yaml
  - item1
  - item2
  ```
  Inline flow syntax (JSON-style) uses brackets: `[item1, item2]`
  Arrays of dictionaries and lists of lists:
  ```yaml
  - name: alice
    age: 30
  - [nested_item1, nested_item2]
  ```
- **Dictionaries / Mappings (Key-Value Pairs):**
  Block style requires a mandatory space after the colon: `key: value`. Deep multi-level indentation must use strictly spaces (NO tabs!):
  ```yaml
  parent:
    child:
      grandchild: "value"
  ```
  Flow style uses braces: `{key: value}`.
- **Multiline Strings:**
  - **Literal Block Scalar (`|`)**: Preserves exact newlines and trailing spaces (ideal for embedded shell scripts or RSA certificates).
    ```yaml
    script: |
      #!/bin/bash
      echo "Line 1"
      echo "Line 2"
    ```
  - **Folded Block Scalar (`>`)**: Replaces newlines with spaces (ideal for long descriptive paragraphs).
    ```yaml
    description: >
      This is a very long paragraph
      that spans multiple lines
      but will be parsed as a single line.
    ```
- **Anchors (`&`), Aliases (`*`), and Merge Keys (`<<: *default`):**
  Define a base template with an anchor `&`, and re-inject properties into downstream blocks using an alias `*` or merge key `<<:`.
  ```yaml
  base_config: &base_config
    cpu: "2"
    memory: "4Gi"
  
  app_service:
    <<: *base_config
    cpu: "4" # Overrides the CPU property
    port: 8080
  ```

### 📦 Essential Tools & Linter Table

| Tool | Purpose | Command Example |
|---|---|---|
| **yamllint** | Linter for YAML files. | `yamllint deploy.yaml` |
| **yq** | Command-line YAML processor. | `yq eval '.spec.replicas' deploy.yaml` |
| **Python PyYAML** | Loading YAML in Python. | `yaml.safe_load(file)` (Never `yaml.load`) |

### Production Working Example

A comprehensive multi-document Kubernetes deployment manifest utilizing YAML anchors and merge keys.

```yaml
---
# Define a common environment anchor
x-common-env: &common_env
  - name: DB_HOST
    value: "postgresql.db.svc.cluster.local"
  - name: LOG_LEVEL
    value: "INFO"

x-security-context: &security_context
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
spec:
  replicas: 3
  template:
    spec:
      securityContext:
        <<: *security_context
      containers:
        - name: auth-app
          image: myreg/auth:v1.2.0
          env: *common_env
          command:
            - /bin/sh
            - -c
            - |
              echo "Starting Auth Service"
              exec /app/binary

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
spec:
  replicas: 2
  template:
    spec:
      securityContext:
        <<: *security_context
      containers:
        - name: payment-app
          image: myreg/payment:v1.1.5
          env:
            # We can merge lists natively in some parsers, but standard YAML 1.1 merge is for maps.
            # Here we just reuse the anchor for the whole list.
            <<: *common_env 
```

**💡 Best Practice:** Always use `yaml.safe_load()` in Python. Standardize on 2-space indents and enforce linting in CI via `yamllint`.

**⚠️ Common Pitfalls:** Mixing tabs and spaces, or forgetting that `yes`, `no`, `on`, `off` are implicitly cast to Booleans in YAML 1.1 (e.g., country code `NO` for Norway becomes `false`).

**🔧 DevOps Pro Tip:** Use `yq` in bash scripts to dynamically patch YAML manifests in CI pipelines before `kubectl apply`.

---

## 3. JSON & JSON Schema Mastery (REST APIs & Cloud Architecture)

**🌐 Analogy:** Standardized Steel Shipping Containers. Strict industrial framing measurements; no decorative sticky notes allowed (no comments!), double quotes mandatory on every label, and trailing commas strictly forbidden!

### What is it? (What & Why)
JSON (JavaScript Object Notation) is a lightweight data-interchange format. It is easy for machines to parse and generate. It forms the backbone of REST APIs, AWS IAM policies, and cloud service payloads.

### Structure & How to Write It (Beginner to Advanced)

- **Primitive Types:** `string`, `number`, `boolean`, `null`, `object` `{}`, `array` `[]`.
- **Formatting Rules:** Double quotes for strings and keys. No trailing commas. No comments.
- **JSON Lines (`.jsonl`):** Each line is a valid JSON object. Perfect for streaming large datasets (logs).
- **JSON Schema:** A vocabulary that allows you to annotate and validate JSON documents.

### 🛠️ Beginner-to-Advanced Syntax & Data Modeling Guide (How to Use It)

- **Objects / Dictionaries (Hash Maps):**
  Written inside curly braces `{}` containing key-value pairs separated by commas. Key names MUST be enclosed in strict double quotation marks (`"key"`, never single quotes `'key'` or bare words!).
  ```json
  {
    "name": "production",
    "region": "us-east-1"
  }
  ```
- **Arrays / Lists:**
  Written inside square brackets `[]` containing ordered collections of values. Collections are zero-indexed positioned.
  ```json
  [1, 2, "three", {"nested": "obj"}, [5, 6], true, null]
  ```
- **Primitive Types:**
  - **Strings:** UTF-8 double quotes, supporting escape sequences (`\n`, `\t`, `\\`, `\"`).
  - **Numbers:** Integers and floating decimals without leading zeros (`07` is invalid), and strictly NO infinity or NaN support!
  - **Booleans:** Strictly lower-case `true` or `false`.
  - **Null:** Strictly lower-case `null`.
- **Grammatical Iron Rules & Pitfalls:**
  - **No Trailing Commas:** A trailing comma after the last item in a dictionary or list is strictly forbidden and will cause instant parser crashes!
    ```json
    {
      "valid": 1,
      "invalid": 2
    }
    ```
  - **No Comments:** Standard JSON completely forbids comments (`//` or `/* */`). If you need comments, you must use distinct variants like JSON-with-Comments (`.jsonc`) or JSON Lines (`.jsonl`).

### 📦 Essential Tools & CLI Table

| Tool | Purpose | Command Example |
|---|---|---|
| **jq** | Command-line JSON processor. | `jq '.Items[].id' data.json` |
| **jsonlint** | Linter/validator. | `jsonlint policy.json` |
| **jsonschema** | CLI validation tool. | `jsonschema -i data.json schema.json` |

### Production Working Example

1) Complete AWS IAM Policy JSON.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-production-bucket/*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": "192.168.1.0/24"
        }
      }
    }
  ]
}
```

2) JSON Schema Draft 2020-12 to validate the above structure.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "IAM Policy",
  "type": "object",
  "properties": {
    "Version": {
      "type": "string",
      "enum": ["2012-10-17", "2008-10-17"]
    },
    "Statement": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["Effect", "Action", "Resource"],
        "properties": {
          "Effect": { "type": "string", "enum": ["Allow", "Deny"] },
          "Action": { "type": ["string", "array"] },
          "Resource": { "type": ["string", "array"] }
        }
      }
    }
  },
  "required": ["Version", "Statement"],
  "additionalProperties": false
}
```

**💡 Best Practice:** Always validate external JSON payloads against a JSON Schema before processing them in your backend to prevent injection attacks and type errors.

**⚠️ Common Pitfalls:** Trailing commas causing parser panics. Integer vs Float type mismatches when handled by strongly typed languages (Go, Rust).

**🔧 DevOps Pro Tip:** Use `jq` to transform API responses dynamically in bash scripts. E.g., `aws ec2 describe-instances | jq '.Reservations[].Instances[] | {InstanceId: .InstanceId, PrivateIp: .PrivateIpAddress}'`.

---

## 4. TOML Mastery (Modern Python Packaging & Rust Configurations)

**🌐 Analogy:** An Organized Apothecary Cabinet with clearly labeled drawers. Unlike deep JSON/YAML nesting that runs far off the right edge of your monitor, TOML keeps configurations organized in clean, shallow named sections (`[table]`, `[[array_of_tables]]`)!

### What is it? (What & Why)
TOML (Tom's Obvious, Minimal Language) is designed for configuration files. It maps unambiguously to a hash table. It is highly readable and resolves the deep indentation issues of YAML. It is the standard for Rust (`Cargo.toml`), Python (`pyproject.toml`), and modern build systems.

### Structure & How to Write It (Beginner to Advanced)

- **Primitives:** String, Integer, Float, Boolean, Offset Date-Time, Local Date-Time, Array.
- **Tables:** Collections of key/value pairs defined by `[table_name]`.
- **Array of Tables:** Defined by `[[array_name]]`. Creates an array of objects.

### 🛠️ Beginner-to-Advanced Syntax & Data Modeling Guide (How to Use It)

- **Key-Value Assignments & Scalars:**
  Keys can be bare (if they contain only letters, numbers, underscores, and dashes) or quoted.
  ```toml
  name = "dev-service"
  "spaced key" = "value"
  port = 8080
  pi = 3.14159
  enabled = true
  ```
- **Strings:**
  - Standard string (double quotes): `"text"`
  - Literal string (single quotes, prevents escaping): `'raw \path\without\escaping'`
  - Multiline basic string: `"""text"""`
  - Multiline literal string: `'''raw text'''`
- **Native Date & Time Primitives:**
  TOML is unique in supporting native RFC 3339 timestamps without wrapping them in string quotes!
  - Full Date-Time: `2026-08-05T16:30:00Z` or with offset `-07:00`
  - Local Date-Time: `2026-08-05T16:30:00`
  - Local Date: `2026-08-05`
  - Local Time: `16:30:00.001`
- **Arrays / Lists:**
  Written inside square brackets, supporting multiline linebreaks and optional trailing commas!
  ```toml
  ports = [ 80, 443, 8080 ]
  hosts = [
    "alpha",
    "omega",
  ]
  ```
- **Inline Tables (Dictionaries):**
  Written inside curly braces on a single line.
  ```toml
  point = { x = 10, y = 20, z = "origin" }
  ```
- **Standard Tables (`[section]`):**
  Declaring clean configuration headers where all subsequent key-values belong to that dictionary namespace until the next header appears!
  ```toml
  [database.primary]
  host = "db1.local"
  port = 5432
  ```
- **Array of Tables (`[[section]]`):**
  Declaring lists of dictionaries using double brackets. Each successive occurrence appends a brand-new object dictionary to that array!
  ```toml
  [[package.dependencies]]
  name = "requests"
  version = "2.31.0"
  
  [[package.dependencies]]
  name = "flask"
  version = "3.0.0"
  ```

### 📦 Essential Tools Table

| Tool | Purpose | Command Example |
|---|---|---|
| **Python tomllib** | Native read library (Python 3.11+). | `import tomllib; tomllib.load(f)` |
| **taplo** | Versatile TOML toolkit (Lint/Format). | `taplo format pyproject.toml` |

### Production Working Example

A production-ready `pyproject.toml` managing packaging, formatting, and testing.

```toml
[tool.poetry]
name = "api-service"
version = "1.0.0"
description = "Core Backend API"
authors = ["DevOps Team <devops@company.com>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "0.100.0"
uvicorn = {extras = ["standard"], version = "0.22.0"}

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I"]
ignore = ["E501"]

[[tool.poetry.source]]
name = "private-repo"
url = "https://pypi.company.com/simple/"
priority = "primary"

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --cov=app"
testpaths = [
    "tests",
]
```

**💡 Best Practice:** Group related keys logically under tables. Avoid deep table nesting; keep it shallow.

**⚠️ Common Pitfalls:** Forgetting to quote string values (unlike YAML, TOML requires quotes for strings). Confusing `[table]` (dictionary) with `[[table]]` (list of dictionaries).

**🔧 DevOps Pro Tip:** When parsing TOML in Python 3.11+, remember `tomllib.load()` requires the file to be opened in binary mode: `open("pyproject.toml", "rb")`.

---

## 5. XML & XPath Mastery (Legacy Enterprise Systems, Maven & SOAP)

**🌐 Analogy:** Matryoshka Russian Nesting Dolls sealed in notary verification tapes. Every opening doll tag (`<pod>`) must enclose its content and terminate with an exact matching closing tag (`</pod>`), validated against legal blueprints (XSD Schemas and DTDs)!

### What is it? (What & Why)
XML (eXtensible Markup Language) is a markup language that defines a set of rules for encoding documents in a format that is both human-readable and machine-readable. Prevalent in enterprise Java (Maven/Spring), .NET, and legacy SOAP APIs.

### Structure & How to Write It (Beginner to Advanced)

- **Elements & Attributes:** `<element attribute="value">content</element>`.
- **Namespaces:** `xmlns:prefix="URI"` to avoid element name conflicts.
- **CDATA:** `<![CDATA[ ... ]]>` for raw data containing `<` or `&` characters.
- **XPath:** A language for selecting nodes from an XML document.

### 🛠️ Beginner-to-Advanced Syntax & Data Modeling Guide (How to Use It)

- **XML Prolog Declaration:**
  The first line should always be `<?xml version="1.0" encoding="UTF-8"?>`. This explicitly declares the document structure for parsers.
- **Elements & Hierarchy:**
  Opening tags (`<container>`), Closing tags (`</container>`), and Empty Self-Closing tags (`<port number="8080"/>`). 
  **Iron Rule:** There must be exactly ONE Single Root Element wrapping the entire document, and tags are strictly case-sensitive (`<Pod>` does not match `</pod>`).
- **Attributes vs Child Elements:**
  Metadata can be written as attributes inside an element's opening tag or as nested child elements. Discussing architectural trade-offs: use an Attribute for simple flat properties/IDs, and use a Child Element for complex, repeating, or structured sub-data!
  ```xml
  <!-- Attribute Style -->
  <user id="1049" role="admin" active="true">John</user>
  
  <!-- Child Element Style -->
  <user>
      <id>1049</id>
      <role>admin</role>
      <active>true</active>
      <name>John</name>
  </user>
  ```
- **Entity References:**
  `<`, `>`, `&`, `"`, and `'` must be written as `&lt;`, `&gt;`, `&amp;`, `&quot;`, and `&apos;` when placed inside ordinary element text.
- **CDATA (Character Data) Blocks:**
  Syntax for embedding unparsed source code scripts or JSON payloads inside XML without escaping characters.
  ```xml
  <query>
      <![CDATA[ SELECT * FROM users WHERE age > 21 & status = 'active'; ]]>
  </query>
  ```
- **Namespaces (`xmlns:`):**
  Avoiding element tag collision across different domain schemas.
  ```xml
  <k8s:pod xmlns:k8s="http://kubernetes.io/schema">
      <k8s:name>app</k8s:name>
  </k8s:pod>
  ```

### 📦 Essential Tools Table

| Tool | Purpose | Command Example |
|---|---|---|
| **xmllint** | Parse and format XML. | `xmllint --format pom.xml` |
| **xpath** | CLI evaluator. | `xpath -e "//version" pom.xml` |
| **defusedxml** | Python security library. | Prevents XXE attacks. |

### Production Working Example

A Java Spring Boot Maven `pom.xml`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" 
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.company</groupId>
    <artifactId>payment-gateway</artifactId>
    <version>2.1.0-SNAPSHOT</version>

    <properties>
        <java.version>17</java.version>
        <spring-boot.version>3.1.0</spring-boot.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <!-- Database Initialization Script CDATA example -->
            <plugin>
                <groupId>org.codehaus.mojo</groupId>
                <artifactId>sql-maven-plugin</artifactId>
                <configuration>
                    <sqlCommand>
                        <![CDATA[
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(100)
                        );
                        ]]>
                    </sqlCommand>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

**💡 Best Practice:** Always use XSD (XML Schema Definition) to validate XML structures. Use `defusedxml` in Python instead of `xml.etree` to prevent Billion Laughs / XXE memory exhaustion attacks.

**⚠️ Common Pitfalls:** Missing closing tags. Not escaping ampersands (`&amp;`) outside of CDATA blocks.

**🔧 DevOps Pro Tip:** Use XPath in CI scripts to extract versions from `pom.xml`: `xmllint --xpath "//*[local-name()='project']/*[local-name()='version']/text()" pom.xml`.

---

## 6. HashiCorp Configuration Language (HCL — Terraform & OpenTofu)

**🌐 Analogy:** Structural Architecture Blueprints equipped with dynamic engineering financial calculators. Unlike static JSON/YAML data files, HCL combines declarative resource blocks with programmatic loops (`for_each`), string interpolation (`"${var.vpc_id}"`), dynamic expression evaluation, and external module references!

### What is it? (What & Why)
HCL is a toolkit for creating structured configuration languages. It is the core language used by Terraform, OpenTofu, Packer, and Vault. It elegantly balances human readability (like YAML) with programmatic capabilities.

### Structure & How to Write It (Beginner to Advanced)

- **Blocks:** `block_type "label1" "label2" { ... }`.
- **Variables & Locals:** `variable "name" {}` and `locals { ... }`.
- **Functions:** Built-in functions like `merge()`, `concat()`, `cidrsubnet()`.
- **Meta-arguments:** `count`, `for_each`, `depends_on`, `lifecycle`.

### 📦 Essential Tools Table

| Tool | Purpose | Command Example |
|---|---|---|
| **terraform fmt** | Format HCL to standard style. | `terraform fmt -recursive` |
| **tflint** | Pluggable linter for Terraform. | `tflint .` |
| **terraform-docs** | Generate documentation from modules. | `terraform-docs markdown .` |

### Production Working Example

An advanced Terraform HCL 2.0 configuration.

```hcl
variable "env" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
}

locals {
  common_tags = {
    Environment = var.env
    ManagedBy   = "Terraform"
  }
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(local.common_tags, { Name = "${var.env}-vpc" })
}

# Dynamic iteration over a map to create subnets
variable "subnets" {
  type = map(object({
    cidr = string
    az   = string
  }))
  default = {
    "public-1a" = { cidr = "10.0.1.0/24", az = "us-east-1a" }
    "public-1b" = { cidr = "10.0.2.0/24", az = "us-east-1b" }
  }
}

resource "aws_subnet" "public" {
  for_each = var.subnets

  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az

  tags = merge(local.common_tags, { Name = "${var.env}-subnet-${each.key}" })
}
```

**💡 Best Practice:** Extensively use `locals` to pre-compute and centralize values instead of scattering complex expressions throughout resource blocks.

**⚠️ Common Pitfalls:** Modifying state directly. Misunderstanding the difference between `count` (list-based, fragile to index changes) and `for_each` (map-based, robust to changes).

**🔧 DevOps Pro Tip:** Run `terraform fmt -check` in your CI/CD pipeline to fail the build if HCL code doesn't meet the canonical formatting standard.

---

## 7. INI & Legacy Flat Property Formats

**🌐 Analogy:** A Simple Hotel Registration Ledger Book. Simple section headings in square brackets (`[section]`) followed by straightforward property assignments (`key = value`).

### What is it? (What & Why)
INI files are a simple standard for configuration. They are flat, extremely readable, but lack complex nesting mechanisms or strict data typing. Widely used for OS configurations, Git, AWS CLI, and Ansible inventories.

### 🛠️ Beginner-to-Advanced Syntax & Data Modeling Guide (How to Use It)

- **Sections & Subsections:**
  Standard bracket headers.
  ```ini
  [myself]
  [branch "main"]
  ```
- **Property Assignments:**
  Using equals signs (`key = value`) or colons (`key : value`).
  ```ini
  key = value
  key : value
  ```
- **Comments:**
  Beginning lines with semicolons (`;`) or hash signs (`#`).
  ```ini
  ; semicolon comment
  # hash sign comment
  ```
- **Value Continuation:**
  Multiline property values using indented line wrap continuation!
  ```ini
  [packages]
  list = 
      package1
      package2
      package3
  ```

### Structure & Production Examples

- **Sections:** `[SectionName]`
- **Properties:** `key = value`
- **Comments:** Lines starting with `;` or `#`

**Ansible Inventory (`hosts.ini`)**
```ini
[webservers]
web1.example.com ansible_user=ubuntu
web2.example.com ansible_user=ubuntu

[dbservers]
db-primary.example.com
db-replica.example.com

[production:children]
webservers
dbservers

[production:vars]
environment=prod
ansible_ssh_private_key_file=~/.ssh/prod_key.pem
```

**AWS Credentials (`~/.aws/credentials`)**
```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

[dev-profile]
aws_access_key_id = AKIAIOSFODNN7DEVKEY
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYDEVSECRET
region = us-west-2
```

**💡 Best Practice:** Keep it simple. If you find yourself encoding lists as comma-separated strings inside INI values, it is time to migrate to TOML or YAML.

**⚠️ Common Pitfalls:** Inconsistent comment characters (`#` vs `;` depending on the parser) and lack of formal Boolean/Integer types (everything parses as a string initially).

**🔧 DevOps Pro Tip:** Use `awk` or `grep` for quick CLI extractions from INI files, or the `crudini` command-line utility for robust programmatic INI modifications in bash scripts.

---

## 8. CLI Conversion & Pipeline Processing Cheat Sheet

**Command Matrix & Workflows:** A practical terminal operational cheat sheet demonstrating live pipelines.

### YAML ↔ JSON Conversions (using `yq`)

Converting YAML to JSON (e.g., to feed Kubernetes manifests to a JSON-only API):
```bash
yq -o=json . kubernetes.yaml > deployment.json
```

Converting JSON back to YAML:
```bash
yq -P . policy.json > policy.yaml
```

### Deep Data Extraction (`jq`)

Extracting nested instance IDs from an AWS API response:
```bash
aws ec2 describe-instances \
  | jq -r '.Reservations[].Instances[] | .InstanceId' > instance_ids.txt
```

Filtering arrays based on conditions (e.g., get only running instances):
```bash
cat instances.json | jq '.Reservations[].Instances[] | select(.State.Name == "running") | .InstanceId'
```

### Pre-commit Hooks & Automated Validation

In a standard DevOps workflow, validate files before they enter the repository using `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/adrienverge/yamllint.git
    rev: v1.32.0
    hooks:
      - id: yamllint
        args: [-c, .yamllint]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: check-json
      - id: check-yaml
      - id: check-toml
      - id: pretty-format-json
        args: [--autofix]
```

**Workflow Summary:**
1. Developer edits `.yaml` or `.json`.
2. `pre-commit` triggers locally, auto-formatting JSON and validating YAML.
3. Code pushed to CI/CD (GitHub Actions/GitLab).
4. CI/CD runs `jsonschema` to ensure the structure conforms to the API specification.
5. Deployments proceed safely, guarded against malformed configurations.
