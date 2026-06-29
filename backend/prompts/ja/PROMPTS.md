# Contract_verify — プロンプトカタログ（日本語）

パイプラインが使用するすべての LLM プロンプトをここに置く。ソースコードには
決して埋め込まない（Foundation Rule i）。各プロンプトは `### キー` 見出しの後に
フェンス付きコードブロックが続く。`{波括弧}` のプレースホルダーは描画時に
`app.prompts.loader.PromptCatalog.render` によって埋め込まれる。

`[TASK:...]`、`[SOURCE]`、`[REQUIREMENT]` のマーカー、JSON のフィールド名、および
列挙値（例: Covered / Compliant / Critical）は英語のまま保持すること。これらは
決定論的なオフラインプロバイダ（`FakeProvider`）が解析し、列挙型に対応づけられる。
日本語にするのは人間向けの指示文のみで、出力の自由記述（notes 等）は日本語で返す。

---

### system_extract
```
あなたは綿密な契約アナリストです。非公式なディール資料（メール、タームシート、
レッドライン）から、具体的で検証可能なビジネス要件を抽出します。要件を捏造する
ことは決してありません。プロローグや散文は出力せず、有効な JSON のみを返します。
```

### extract_requirements
```
[TASK:EXTRACT]
以下の SOURCE に記載されている具体的なビジネス要件をすべて抽出してください。
要件とは、支払条件、納期、SLA クレジット、データ削除義務、責任上限など、
具体的で確認可能な要求を指します。

各要件について、次のフィールドを持つオブジェクトを返してください。
  - item_id   : "r-001" のような短い ID
  - text      : 要件を 1 つの明確な文で表したもの（日本語で記述）
  - type      : payment, data, SLA, delivery, liability, IP,
                confidentiality, governing_law, general のいずれか
  - priority  : Critical | High | Medium | Low
  - binding   : 署名済み資料またはタームシート由来なら true、そうでなければ false

これらのオブジェクトの JSON 配列のみを返してください。注釈は含めないでください。

[SOURCE]
{source_text}
[/SOURCE]
```

### system_verify
```
あなたは契約検証エンジンです。1 つのビジネス要件と、契約書から取得された候補条項が
与えられたとき、契約が要件を満たしているかを判断し、根拠とした条項を引用します。
有効な JSON のみを返します。
```

### verify_requirement
```
[TASK:VERIFY]
CONTRACT の条項が REQUIREMENT を満たしているかを判断してください。

次の JSON オブジェクトを返してください。
  - status              : Covered | Partial | Missing | Contradicted
  - matched_clause_ids  : 根拠とした条項の block_id の配列（空でも可）
  - llm_confidence      : この判断に対する確信度 0.0〜1.0
  - notes               : 根拠を 1 文で簡潔に（日本語で記述）

[REQUIREMENT]
{requirement_text}
[/REQUIREMENT]

[SOURCE]
{clauses}
[/SOURCE]
```

### verify_playbook
```
[TASK:VERIFY]
REQUIREMENT は、ルール "{rule}" を持つ会社プレイブックの方針です。CONTRACT が
これに準拠しているかを判断してください。

次の JSON を返してください。
  - status              : Compliant | Deviation | Violation
  - matched_clause_ids  : 条項の block_id の配列
  - llm_confidence      : 0.0〜1.0
  - notes               : 1 文で簡潔に（日本語で記述）

[REQUIREMENT]
{requirement_text}
[/REQUIREMENT]

[SOURCE]
{clauses}
[/SOURCE]
```

### verify_standard_term
```
[TASK:VERIFY]
REQUIREMENT は、この契約類型で期待される標準的な市場条項です。CONTRACT に
それが含まれているかを判断してください。

次の JSON を返してください。
  - status              : Present | Missing | Non-standard
  - matched_clause_ids  : 条項の block_id の配列
  - llm_confidence      : 0.0〜1.0
  - notes               : 1 文で簡潔に（日本語で記述）

[REQUIREMENT]
{requirement_text}
[/REQUIREMENT]

[SOURCE]
{clauses}
[/SOURCE]
```

### system_extract_library
```
あなたは綿密な契約アナリストです。会社のポリシー文書や市場標準の条項ライブラリから、
構造化された条項方針および標準条項を抽出します。項目を捏造することは決してありません。
散文は出力せず、有効な JSON のみを返します。
```

### extract_playbook_positions
```
[TASK:EXTRACT_PLAYBOOK]
以下の COMPANY PLAYBOOK 文書から、契約ポリシー方針をすべて抽出してください。
方針とは、契約条項に関する具体的な要求・制限・推奨スタンス（例: 責任上限のルール、
支払条件の要求、秘密保持の選好）を指します。

各方針について、次のフィールドを持つオブジェクトを返してください。
  - text     : 方針を 1 つの明確で自己完結した文で表したもの（日本語で記述）
  - type     : liability, payment, confidentiality, data, SLA,
               delivery, IP, indemnity, governing_law, general のいずれか
  - priority : Critical | High | Medium | Low
  - rule     : must_have     （必須 — 「しなければならない」「要する」）
             | must_not_have （禁止 — 「してはならない」「禁止」）
             | preferred     （標準的な要求・交渉可能 — 「すべき」「望ましい」）

各条項の文言から "rule" を推測してください。これらのオブジェクトの JSON 配列のみを
返してください。散文・注釈・マークダウンのラッパーは含めないでください。

[SOURCE]
{source_text}
[/SOURCE]
```

### extract_standard_terms
```
[TASK:EXTRACT_STANDARD_TERMS]
以下の DOCUMENT に記載されている標準契約条項をすべて抽出してください。
標準条項とは、該当類型の適切に整備された商取引契約において市場慣行が期待する
条項または保護を指します。

各条項について、次のフィールドを持つオブジェクトを返してください。
  - text          : 条項を 1 つの明確で自己完結した文で表したもの（日本語で記述）
  - type          : liability, payment, confidentiality, data, SLA,
                    delivery, IP, indemnity, governing_law, general のいずれか
  - priority      : Critical | High | Medium | Low
  - contract_type : この条項が適用される契約類型（例: services, msa, nda,
                    employment）。一般的に適用される場合は null

これらのオブジェクトの JSON 配列のみを返してください。散文・注釈は含めないでください。

[SOURCE]
{source_text}
[/SOURCE]
```

### report_summary
```
[TASK:SUMMARIZE]
以下の検証結果について、法律家でないビジネス担当者向けに、平易な日本語で短い
要約を書いてください。まずカバレッジの結果を述べ、次に最も重要なギャップを挙げます。
2〜4 文で。法的助言は行わないでください。

[SOURCE]
Coverage score: {coverage_score}
Gaps: {gaps}
[/SOURCE]
```
