<!-- AUTO-GENERATED from act_taxonomy.ttl by generate_artifacts.py on 2026-10-03. DO NOT EDIT BY HAND. Edit the TTL and re-run. -->

# ACT Annotation Guideline

For human annotators. Each ActionType lists its definition, scope note (boundaries), and vocabulary examples.

## Operational notes

- MULTILABEL: A separate resource (act_multilabel.ttl) records expressions that map to more than one ActionType. Multilabel is NOT expressed via skos:broader here (broader is reserved for the category hierarchy).
- AFFIX NORMALIZATION RULES (type-level): 〜開始 => {head-class, Beginning} multilabel; 〜化 => Transformation by default; 再〜 => {stem-class, Repetition} multilabel; use Revival only when stem itself denotes restoration (復活・回復・再興); light verbs (する/なる/おく/うける) => General.
- KNOWN LIMITATION: This is a context-independent, type-level dictionary. Agent/Theme-dependent boundary cases (e.g. 派遣 Military vs Diplomatic) have no single type-level answer by design.
- PROVISIONAL ITEMS: Authorization internal split (interpersonal vs institutional); CulturalExpression future split into CulturalProduction / ReligiousPractice (threshold n>=10); modern-era vocabulary gap (e.g. 打ち上げ).

## 軍事・暴力・抑圧 / Military, Violence & Suppression

_軍事力・暴力、および他者の抑圧に関連する行為。 / Actions related to military force, violence, and the suppression of others._

### AssassinationMassacre — 暗殺・虐殺 / Assassination Massacre
- **Definition (JA)**: 意図的かつ非正当な殺害。
- **Definition (EN)**: The intentional and illegitimate killing of one or more persons.
- **Scope note**: Intentional, illegitimate killing. Natural death and battlefield death are Death.
- **Examples (JA)**: 暗殺・爆殺・射殺・虐殺・粛清・殺害・毒殺・殺戮
- **Examples (EN)**: assassinate, massacre, purge

### CaptureAndPunishment — 拘束・処罰 / Capture And Punishment
- **Definition (JA)**: 人物の拘束・勾留・司法的処罰。
- **Definition (EN)**: The capture, detention, or judicial punishment of a person.
- **Examples (JA)**: 逮捕・捕縛・拉致・配流・処刑・斬首・刑死・捕囚・監禁
- **Examples (EN)**: arrest, imprison, execute, exile

### ConquestOccupation — 征服・占領 / Conquest Occupation
- **Definition (JA)**: ある領域・政体に対する支配の確立（征服する側の視点）。
- **Definition (EN)**: The active establishment of control over a territory or polity, from the conqueror's perspective.
- **Scope note**: Agent = the conquering side (active acquisition of control). The subjugated side's perspective (服属・臣従) is Subjugation. A single defeat event is Defeat; the resulting establishment of ongoing domination is here.
- **Examples (JA)**: 征服・占領・占拠・制圧・支配・領有・支配下におく・駐留
- **Examples (EN)**: conquer, occupy, annex

### Defeat — 敗北・降伏 / Defeat
- **Definition (JA)**: 個別の出来事としての軍事的敗北（敗れる側の視点）。
- **Definition (EN)**: A military defeat as a discrete event, from the losing side's perspective.
- **Scope note**: A discrete military defeat event. Ongoing subordination as a relationship is Subjugation; establishing domination from the winner's side is ConquestOccupation.
- **Examples (JA)**: 敗北・大敗・惨敗・降伏・投降・撤退・敗走
- **Examples (EN)**: defeat, surrender, retreat

### DisputeConflict — 紛争・衝突 / Dispute Conflict
- **Definition (JA)**: 勢力間の武力衝突または交戦状態。
- **Definition (EN)**: An armed clash or state of hostilities between parties.
- **Scope note**: Mutual armed hostilities, including civil war (内戦). Distinguished from MilitaryAttack (one-sided offensive) and RevoltInsurrection (non-state uprising against authority).
- **Examples (JA)**: 衝突・抗争・参戦・内戦・交戦・武力衝突・戦闘・戦争
- **Examples (EN)**: clash, war, civil war, combat

### MilitaryAttack — 軍事攻撃 / Military Attack
- **Definition (JA)**: ある勢力が他勢力に対して仕掛ける軍事的な攻勢行為。
- **Definition (EN)**: An armed offensive action launched by one party against another.
- **Examples (JA)**: 攻撃・侵攻・侵入・包囲・攻略・撃退・進軍・出兵・上陸・進出
- **Examples (EN)**: attack, invade, besiege, advance

### Subjugation — 服属・臣従 / Subjugation
- **Definition (JA)**: 服属・従属関係の確立（服属する側の視点）。
- **Definition (EN)**: Establishment of a subordination/vassalage relationship, described from the subordinated side's perspective.
- **Scope note**: Counterpart of ConquestOccupation (which takes the conqueror's perspective). Kept as a separate class to preserve Agent-perspective in action-centric queries (a ConquestOccupation query should return conquerors, not the subjugated).
- **Examples (JA)**: 服属・臣従する・支配下に入る・服従・帰順
- **Examples (EN)**: submit, become a vassal

### Suppression — 弾圧・抑圧 / Suppression
- **Definition (JA)**: 権力側による弾圧・禁止行為（抑圧する側の視点）。
- **Definition (EN)**: Coercive action by an authority to suppress or prohibit, from the suppressing side.
- **Scope note**: The suppressing side's action. Refusal/negation by the resisting side is Rejection; organized protest movements are ResistanceProtest.
- **Examples (JA)**: 弾圧・鎮圧・迫害・排除・禁止・布教禁止・非合法化
- **Examples (EN)**: suppress, persecute, ban

### Victory — 勝利 / Victory
- **Definition (JA)**: 軍事的交戦における勝利という結果。
- **Definition (EN)**: A successful outcome of a military engagement.
- **Scope note**: Rare class (n<5 in benchmark corpus); excluded from cross-validation.
- **Examples (JA)**: 勝利・大勝・平定・撃破・完勝・戦勝
- **Examples (EN)**: victory, triumph, rout

## 集団抵抗・反乱 / Collective Resistance & Revolt

_国家以外の立場からの、武装・非武装を問わない権力への集団的行動。 / Armed or unarmed collective action against authority, from a non-state actor's perspective._

### ResistanceProtest — 抵抗・抗議 / Resistance Protest
- **Definition (JA)**: 抗議・抵抗による組織的・継続的な反対の表明。
- **Definition (EN)**: Organized or sustained opposition expressed through protest or resistance.
- **Scope note**: Organized / sustained opposition movements. A single act of refusal or negation (拒否・否定) is Rejection.
- **Examples (JA)**: 抵抗・抗議・反対・ボイコット・デモ・批判・請願・独立運動
- **Examples (EN)**: resist, protest, boycott, petition

### RevoltInsurrection — 反乱・革命 / Revolt Insurrection
- **Definition (JA)**: 既存権力に対する武装蜂起・革命的行動。
- **Definition (EN)**: An armed uprising or revolutionary action against an established authority.
- **Examples (JA)**: 反乱・蜂起・一揆・暴動・革命・クーデター・挙兵・内戦
- **Examples (EN)**: revolt, uprising, revolution, coup

## 外交・関係 / Diplomacy & Relations

_外交・交渉・合意、および勢力間の関係に関連する行為。 / Actions related to diplomacy, negotiation, agreements, and inter-party relations._

### Authorization — 許可・承認 / Authorization
- **Definition (JA)**: 公式な許可・承認の付与。
- **Definition (EN)**: An official granting of permission or approval.
- **Scope note**: Counterpart of Rejection.
- **Examples (JA)**: 許可・緩和・認定・公認・許す・承認・独立承認
- **Examples (EN)**: permit, approve, authorize, recognize

### Communication — 意見表明・言明 / Communication
- **Definition (JA)**: 強制力を伴わない非公式な発話行為（主張・説得・提唱・約束など）。
- **Definition (EN)**: Non-coercive, non-official speech acts: asserting, persuading, proposing, promising.
- **Scope note**: Distinct from Declaration (official/outward) and DemandOrder (coercive). A non-coercive speech act placed under Diplomacy & Relations.
- **Examples (JA)**: 主張・説得・提唱・提示・約束
- **Examples (EN)**: assert, persuade, propose, promise

### ConflictRupture — 対立・断交 / Conflict Rupture
- **Definition (JA)**: 関係・同盟・合意の断絶・決裂。
- **Definition (EN)**: The rupture or breakdown of a relationship, alliance, or agreement.
- **Examples (JA)**: 対立・断交・破棄・離反・脱退・絶交・決裂・国交断絶
- **Examples (EN)**: rupture, sever ties, withdraw

### Declaration — 宣言・布告 / Declaration
- **Definition (JA)**: 公式・対外的な宣言・布告。
- **Definition (EN)**: An official or outward public declaration.
- **Scope note**: Official / outward public speech acts. Persuasive or assertive speech (主張・説得) is Communication; demands/orders are DemandOrder.
- **Examples (JA)**: 宣言・独立宣言・宣戦布告・通告・布告・発効・声明・表明
- **Examples (EN)**: declare, proclaim, announce

### DemandOrder — 要求・命令 / Demand Order
- **Definition (JA)**: 強制力を伴う発話行為（要求・命令）。
- **Definition (EN)**: A speech act carrying compulsory force, such as a demand or order.
- **Scope note**: Speech acts with compulsory force. Non-coercive assertion/persuasion is Communication.
- **Examples (JA)**: 要求・要請・命令・発令・通達・勧告・最後通牒・警告
- **Examples (EN)**: demand, order, ultimatum

### DiplomaticNegotiation — 外交交渉 / Diplomatic Negotiation
- **Definition (JA)**: 勢力間の外交的接触・交渉。
- **Definition (EN)**: Diplomatic contact or negotiation between parties.
- **Examples (JA)**: 交渉・調停・仲介・会見・会談・訪問・遣使・謁見・協議
- **Examples (EN)**: negotiate, mediate, confer

### Rejection — 拒否・否定 / Rejection
- **Definition (JA)**: 提案・要求・主張・条約等に対する不同意の意思表示。
- **Definition (EN)**: An expression of non-consent toward a proposal, demand, assertion, or treaty: refusal, negation, rejection, veto.
- **Scope note**: Defined as a negative speech act, independent of political context. Organized opposition movements are ResistanceProtest; the suppressing side's prohibitive action is Suppression. Counterpart of Authorization.
- **Examples (JA)**: 拒否・否定・拒絶・否決・却下・批准拒否・調印拒否
- **Examples (EN)**: refuse, reject, veto, deny

### TreatyAgreement — 条約・合意 / Treaty Agreement
- **Definition (JA)**: 条約・公式合意の締結・批准。
- **Definition (EN)**: The conclusion or ratification of a treaty or formal agreement.
- **Examples (JA)**: 締結・調印・批准・同盟・和約・和平・承認・受諾・合意
- **Examples (EN)**: conclude a treaty, ratify, alliance

## 政治・制度 / Political & Institutional

_政治的地位・統治、および制度・法の変更に関連する行為。 / Actions related to political office, governance, and institutional or legal change._

### Abdication — 退位・失脚 / Abdication
- **Definition (JA)**: 王位・官職・公的地位からの離脱。
- **Definition (EN)**: Leaving a throne, office, or official position.
- **Examples (JA)**: 退位・辞職・失脚・退陣・解任・廃位・総辞職・引退
- **Examples (EN)**: abdicate, resign, be dismissed

### Accession — 即位・就任 / Accession
- **Definition (JA)**: 王位・官職・公的地位への就任。
- **Definition (EN)**: Assuming a throne, office, or official position.
- **Examples (JA)**: 即位・戴冠・就任・任命・冊封・選出・当選・再即位
- **Examples (EN)**: accede, enthrone, appoint

### Legislation — 制定・立法 / Legislation
- **Definition (JA)**: 法・制度の制定・公布・改革。
- **Definition (EN)**: The enactment, promulgation, or reform of laws and institutional rules.
- **Examples (JA)**: 制定・公布・発布・施行・改革・改正・採択・決議・可決
- **Examples (EN)**: enact, promulgate, reform, adopt

## 存在・ライフサイクル / Existence & Lifecycle

_主体（人物・国家・組織・政体）の存在とライフサイクル、すなわち発生・終焉・分離に関連する行為。 / Actions concerning the existence and lifecycle of a subject (a person, state, organisation, or polity): its coming into being, ending, and separation._

### Beginning — 誕生・始まり / Beginning
- **Definition (JA)**: 出来事・現象・存在の発生・開始。
- **Definition (EN)**: The coming into being or onset of an event, phenomenon, or entity.
- **Scope note**: Also the fallback label for 〜開始 compounds (which receive {head-class, Beginning} multilabel).
- **Examples (JA)**: 誕生・生まれる・開始・始まる・登場・起こる・勃発・発生
- **Examples (EN)**: begin, arise, break out, emerge

### Death — 死亡 / Death
- **Definition (JA)**: 人物の自然死または戦死。
- **Definition (EN)**: The natural or battlefield death of a person.
- **Scope note**: Natural death and battlefield death. Intentional killing is AssassinationMassacre.
- **Examples (JA)**: 死去・死亡・没・崩御・戦死・病死・敗死・薨去
- **Examples (EN)**: die, pass away, die in battle

### Dissolution — 滅亡・解体 / Dissolution
- **Definition (JA)**: 主体の消滅、または出来事・プロセスの確定的終了。
- **Definition (EN)**: The disappearance of a subject or the definitive termination of an event or process.
- **Scope note**: Covers both the disappearance of a subject (滅亡・崩壊) and the definitive end of a process (終了・中止・打ち切り・終わる). Temporary/resumable cessation is Suspension; gradual decline of scale is De-escalation.
- **Examples (JA)**: 滅亡・崩壊・解体・解散・廃止・終結・消滅・壊滅・終了・中止・打ち切り・終わる
- **Examples (EN)**: fall, collapse, dissolve, terminate

### Foundation — 建国・成立 / Foundation
- **Definition (JA)**: 国家・組織・体制の建国・設立。
- **Definition (EN)**: The founding or formal establishment of a state, organization, or system.
- **Examples (JA)**: 成立・建国・樹立・創設・設立・結成・発足・建立・統一
- **Examples (EN)**: found, establish, form

### IndependenceSeparation — 独立・分離 / Independence Separation
- **Definition (JA)**: 政体の独立獲得・分離。
- **Definition (EN)**: The gaining of independence or separation of a polity from another.
- **Examples (JA)**: 独立・再独立・分離独立・分裂・自立・分立・自治
- **Examples (EN)**: gain independence, secede, split

## 文化・経済・知識 / Culture, Economy & Knowledge

_文化・宗教・経済、および科学など知の生産に関連する行為。 / Actions related to cultural, religious, economic, scientific, and knowledge-producing activity._

### ConstructionProduction — 建設・生産 / Construction Production
- **Definition (JA)**: 物理的な構造物・物品の建設・製造・生産。
- **Definition (EN)**: The construction, manufacture, or production of physical works or goods.
- **Examples (JA)**: 建設・建造・建築・製造・鋳造・着工・完成・作成・開発・竣工
- **Examples (EN)**: build, construct, manufacture

### CulturalExpression — 文化・宗教・創作 / Cultural Expression
- **Definition (JA)**: 文化的・創作的・宗教的な表現および実践。
- **Definition (EN)**: Cultural, creative, or religious expression and practice.
- **Scope note**: Subsumes both creative/cultural production and religious practice. PROVISIONAL future split into CulturalProduction (著す・執筆・刊行・初演・放送) and ReligiousPractice (布教・伝来・改宗・列聖), to be introduced only if each candidate reaches n>=10.
- **Examples (JA)**: 布教・伝来・伝道・改宗・列聖・刊行・著す・執筆・創作・初演・撮影・出版・放送
- **Examples (EN)**: preach, publish, compose, perform

### ExplorationDiscovery — 探検・発見 / Exploration Discovery
- **Definition (JA)**: 探検・発見の行為。
- **Definition (EN)**: An act of exploration or discovery.
- **Scope note**: Intentional exploratory acts. Unintentional arrival (漂着) is Movement.
- **Examples (JA)**: 探検・発見・航海・世界周航・世界一周・調査・登頂・踏査・開拓
- **Examples (EN)**: explore, discover, voyage, survey

### ScientificInvention — 科学・技術・発明 / Scientific Invention
- **Definition (JA)**: 科学的・技術的な発明・発見・研究。
- **Definition (EN)**: Scientific or technological invention, discovery, or research.
- **Scope note**: PROVISIONAL: modern-era vocabulary (e.g. 打ち上げ) sits at the Movement / ScientificInvention boundary; logged as a future expansion candidate.
- **Examples (JA)**: 発明・発見・改良・発達・解明・実験・研究・開発・設計・打ち上げ
- **Examples (EN)**: invent, discover, experiment

### TradeEconomy — 通商・経済 / Trade Economy
- **Definition (JA)**: 商業・貿易・経済活動。
- **Definition (EN)**: Commercial, trade, or economic activity.
- **Scope note**: Includes commissioning/opening of trade & transport infrastructure (開通・就航) as a corpus-specific economic reading. Pure possession transfer without an economic frame (授与・寄進) is PossessionTransfer.
- **Examples (JA)**: 通商・貿易・販売・輸入・輸出・開港・課税・略奪・採掘・金融・開通・就航
- **Examples (EN)**: trade, import, export, tax

## 汎用 / General

_特定の主題カテゴリに属さない、汎用的・ドメイン中立な行為。 / General or domain-neutral actions that do not belong to a specific thematic category._

### Failure — 失敗 / Failure
- **Definition (JA)**: 目的・企ての失敗・挫折。
- **Definition (EN)**: The failure or frustration of an aim or undertaking.
- **Scope note**: Rare class (n<5 in benchmark corpus); excluded from cross-validation.
- **Examples (JA)**: 失敗・挫折・未遂・頓挫・失敗に終わる
- **Examples (EN)**: fail, be frustrated, abort

### General — 一般・汎用 / General
- **Definition (JA)**: ドメイン中立、または単独では特定ActionTypeに確定しない意味的に未指定の動作。
- **Definition (EN)**: Domain-neutral or semantically underspecified actions that do not resolve to a specific ActionType on their own.
- **Scope note**: Includes light/function verbs (する・なる・おく・うける) and words whose citation sense does not converge on a single domain (競争・流入・干渉・定着).
- **Examples (JA)**: 参加・計画・実施・展開・活動・なる・する・流入・干渉・定着
- **Examples (EN)**: participate, plan, carry out, become

### PossessionTransfer — 授与・移譲 / Possession Transfer
- **Definition (JA)**: 経済的枠組みを伴わない、物品・称号・権利の一方から他方への移転。
- **Definition (EN)**: Transfer of possession of an object, title, or right from one party to another, without an inherent commercial frame.
- **Scope note**: Absorbs the tribute vocabulary (朝貢・献上). Commercial exchange is TradeEconomy.
- **Examples (JA)**: 授与・寄進・あたえる・付与・得る・朝貢・献上
- **Examples (EN)**: grant, bestow, endow, pay tribute

### Success — 成功 / Success
- **Definition (JA)**: 目的・企ての達成・成功。
- **Definition (EN)**: The successful accomplishment of an aim or undertaking.
- **Scope note**: Rare class (n<5 in benchmark corpus); excluded from cross-validation.
- **Examples (JA)**: 成功・達成・完遂・実現・果たす・成就
- **Examples (EN)**: succeed, accomplish, achieve

## 状態・変遷 / State & Transition

_既存の主体の状態・程度・位置・継続性の変化に関連する行為（移動・増減・変容・中断・解放など）。 / Actions concerning a change in the state, degree, position, or continuity of an existing subject: movement, escalation, transformation, suspension, and release._

### DeEscalation — 縮小・減退 / De-escalation
- **Definition (JA)**: 規模・強度・程度の縮小・減衰（存在はするが弱まる）。
- **Definition (EN)**: Decrease or gradual decline in scale, intensity, or degree (still existing, but weakening).
- **Scope note**: Counterpart of Escalation. Distinct from Suspension (temporary halt) and Dissolution (disappearance). 衰退 (gradual decline) belongs here; 滅亡 (disappearance at a point) stays in Dissolution.
- **Examples (JA)**: 衰退・縮小・弱体化・後退・鎮静化・減退
- **Examples (EN)**: decline, shrink, weaken

### Escalation — 拡大・激化 / Escalation
- **Definition (JA)**: 規模・強度・程度の増大。
- **Definition (EN)**: Increase in scale, intensity, or degree.
- **Scope note**: Restricted to the increase direction only. Decrease/decline (縮小・衰退・急減) is De-escalation.
- **Examples (JA)**: 拡大・強化・激化・過激化・増大・躍進・勢力拡大・本格化
- **Examples (EN)**: expand, intensify, escalate

### Movement — 移動・遷都 / Movement
- **Definition (JA)**: 人・集団・首都の物理的移動。
- **Definition (EN)**: Physical relocation of persons, groups, or a capital.
- **Scope note**: Physical relocation without inherent intent of exploration/discovery. Intentional exploratory travel (世界一周・航海) is ExplorationDiscovery; unintentional arrival (漂着) stays here.
- **Examples (JA)**: 遷都・移転・移住・移民・行く・出発・到達・漂着・来航・亡命・帰国
- **Examples (EN)**: relocate, migrate, arrive, flee

### Release — 解放・返還 / Release
- **Definition (JA)**: 人物・領域・制限の解放・返還・解除。
- **Definition (EN)**: The release, return, or lifting of a person, territory, or restriction.
- **Scope note**: Rare class (n<5 in benchmark corpus); excluded from cross-validation.
- **Examples (JA)**: 解放・釈放・返還・撤回・引き渡し・解除・撤廃・特赦
- **Examples (EN)**: release, return, lift, pardon

### Repetition — 反復・再 / Repetition
- **Definition (JA)**: 以前に起きた動作・出来事が再び起こること。接頭辞「再」が示すアスペクト標識。
- **Definition (EN)**: The recurrence of an action or event that has happened before; an aspectual marker signalled by the 再 prefix.
- **Scope note**: Aspectual counterpart of Beginning (for 開始). 再〜 compounds receive a {stem-class, Repetition} multilabel. Revival is assigned only when the stem itself means restoration (復活・回復・再興), not merely because of the 再 prefix.
- **Examples (JA)**: 再襲来・再奪回・再認定・再軍備・再結成
- **Examples (EN)**: recur, happen again, resume

### Revival — 復興・回復 / Revival
- **Definition (JA)**: かつて存在した実体・状態の復興・回復。
- **Definition (EN)**: The restoration or revival of a previously existing entity or state.
- **Scope note**: Assigned when the stem itself denotes restoration (復活・回復・再興). Generic 再〜 compounds use {stem-class, Repetition} multilabel instead; Revival is not triggered by the 再 prefix alone.
- **Examples (JA)**: 再建・復活・復興・再興・回復・復帰・再生・再統一・名誉回復
- **Examples (EN)**: revive, restore, rebuild

### Suspension — 中断・停止 / Suspension
- **Definition (JA)**: 活動・プロセスの一時的・再開可能な停止。
- **Definition (EN)**: Temporary, resumable cessation of an activity or process.
- **Scope note**: Temporary, resumable cessation only. Conclusive termination (終了・中止・打ち切り) is Dissolution.
- **Examples (JA)**: 停止・中断・休戦・停戦・収束・沈静化・休業・停滞・更新せず
- **Examples (EN)**: suspend, halt, truce, stagnate

### Transformation — 変容・転換 / Transformation
- **Definition (JA)**: 状態・性質の変化（多くは「〜化」で表現）。
- **Definition (EN)**: A change of state or nature, typically expressed by the '-ka' suffix.
- **Scope note**: Default class for 〜化 compounds (state change). Where the stem has a strong domain pull (e.g. 自治領化), treat as multilabel.
- **Examples (JA)**: 改宗・イスラーム化・民主化・近代化・国有化・西洋化・独裁化・公然化・表面化
- **Examples (EN)**: convert, democratize, nationalize

