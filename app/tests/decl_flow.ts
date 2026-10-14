// U52-5 ön uç statik taraması, veri akışı hâli (FAZ3_APP_AUDIT B2). Satır-yerel tarama yalnız `api.`
// geçen satırlara bakıyordu; beyandan bir satır önce türetilen j (mutasyon e2) görünmüyordu.
//
// Yöntem: TypeScript AST'sinde beyan durumunun her geçişi (`declared`, `declDropped`,
// `observed_streak_user`, `userDays`, `declaredDays`) ifade ağacında yukarı doğru izlenir. Değer bir
// yerel değişkene atanırsa o değişken de kirlenir ve her kullanımı aynı kuralla izlenir. Akış YALNIZ
// şu havuzlarda biter; başka her yer (komut argümanı, j/jSelected, koşul, dönüş, başka durum alanı) ihlaldir:
//   1. beyan işleyicisi: `case "declare"` / `case "clear-declarations"` içinde beyan durumunun
//      kendisine atama (aç/kapa, temizle);
//   2. senaryo kaydetme: `save()` içinde istek nesnesinin `observed_streak_user` alanı;
//   3. `resetView(...)` argümanı (kişisel kayıt yükleme, formu yenileyince beyanı koruma);
//      (`declaredDays(...)` saf biçim dönüştürücüsüdür, akış onun sonucundan sürer; başka HER
//      fonksiyon ya da komut argümanı ihlaldir);
//   4. şerit etiketi render'ına AYNEN taşıma: `renderConditional({ declared: x.declared, … })` /
//      `renderRecordPage({ … })` / `renderCeilingSummary({ … })` (EK 3 U62) nesnesinde aynı adlı alanın düz kopyası (SPEC_APP U52-5: "beyan
//      durumu yalnız şerit etiketi render'ında ve senaryo kayıt modülünde geçer"; render DOM
//      taraması U52-1…4'te).
import ts from "typescript";

export const DECL_IDS = new Set(["declared", "declDropped", "observed_streak_user", "userDays", "declaredDays"]);
const HANDLER_CASES = new Set(["declare", "clear-declarations"]);
// EK 3 U62: U52 kümesi Tavan serisi kartına genişler (kart beyanı yalnız "önde mi" etiketi için okur)
const RENDER_SINKS = new Set(["renderConditional", "renderRecordPage", "renderCeilingSummary"]);
const STATE_FIELDS = new Set(["declared", "declDropped"]);

export interface FlowViolation {
  file: string;
  line: number;
  text: string;
  why: string;
}

function calleeName(c: ts.CallExpression): string | null {
  const e = c.expression;
  if (ts.isIdentifier(e)) return e.text;
  if (ts.isPropertyAccessExpression(e)) return e.name.text;
  return null;
}

function propName(p: ts.PropertyAssignment | ts.ShorthandPropertyAssignment): string | null {
  return ts.isIdentifier(p.name) || ts.isStringLiteral(p.name) ? p.name.text : null;
}

/** `x.declared`, `x.declared[i]`, `x.declDropped`: beyan durumunun kendisi. */
function isDeclTarget(e: ts.Expression): boolean {
  if (ts.isElementAccessExpression(e)) return isDeclTarget(e.expression);
  return ts.isPropertyAccessExpression(e) && STATE_FIELDS.has(e.name.text);
}

function inHandlerCase(n: ts.Node): boolean {
  for (let p: ts.Node | undefined = n; p; p = p.parent) {
    if (ts.isCaseClause(p)) return ts.isStringLiteral(p.expression) && HANDLER_CASES.has(p.expression.text);
    if (ts.isFunctionLike(p)) return false;
  }
  return false;
}

function enclosingFunctionName(n: ts.Node): string | null {
  for (let p: ts.Node | undefined = n.parent; p; p = p.parent) {
    if (ts.isFunctionDeclaration(p)) return p.name?.text ?? null;
    if (ts.isFunctionLike(p)) return null;
  }
  return null;
}

function scopeOf(n: ts.Node): ts.Node {
  for (let p: ts.Node | undefined = n.parent; p; p = p.parent) {
    if (ts.isFunctionLike(p) || ts.isSourceFile(p)) return p;
  }
  return n.getSourceFile();
}

/** Tanımlayıcı bir değişkene mi başvuruyor (özellik adı ya da nesne anahtarı değil)? */
function isReference(id: ts.Identifier): boolean {
  const p = id.parent;
  if (ts.isPropertyAccessExpression(p) && p.name === id) return false;
  if ((ts.isPropertyAssignment(p) || ts.isPropertyDeclaration(p) || ts.isPropertySignature(p)) && p.name === id) return false;
  if (ts.isVariableDeclaration(p) && p.name === id) return false;
  return true;
}

export function declFlowViolations(file: string, source: string): FlowViolation[] {
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.ES2022, true, ts.ScriptKind.TS);
  const lines = source.split("\n");
  const out: FlowViolation[] = [];
  const tainted = new Set<string>();

  const report = (n: ts.Node, why: string) => {
    const line = sf.getLineAndCharacterOfPosition(n.getStart(sf)).line;
    out.push({ file, line: line + 1, text: lines[line].trim(), why });
  };

  const taintVar = (name: string, decl: ts.Node, origin: string) => {
    const scope = scopeOf(decl);
    const key = `${name}@${scope.pos}`;
    if (tainted.has(key)) return;
    tainted.add(key);
    const refs: ts.Identifier[] = [];
    const walk = (n: ts.Node) => {
      if (ts.isIdentifier(n) && n.text === name && isReference(n)) refs.push(n);
      ts.forEachChild(n, walk);
    };
    walk(scope);
    for (const r of refs) follow(r, `${origin} → ${name}`);
  };

  // Değer ağaçta yukarı izlenir; havuza varırsa biter, sınırda ihlal.
  function follow(start: ts.Node, origin: string): void {
    let cur: ts.Node = start;
    for (;;) {
      const p = cur.parent;
      if (!p || ts.isSourceFile(p)) return report(start, `${origin}: akış bir havuza ulaşmadı`);
      if (ts.isCallExpression(p) && p.arguments.some((a) => a === cur)) {
        const callee = calleeName(p) ?? p.expression.getText(sf);
        // 3. resetView argümanı
        if (callee === "resetView") return;
        // `declaredDays`: beyanı kişisel kayıt biçimine çeviren saf dönüştürücü (state.ts); akış sürer
        if (callee !== "declaredDays") return report(start, `${origin}: fonksiyon/komut argümanı (${p.expression.getText(sf)})`);
      }
      if (ts.isPropertyAssignment(p) && (cur === p.initializer || cur === p.name)) {
        const name = propName(p);
        // 4. şerit etiketi render'ına aynen taşıma
        const init = p.initializer;
        const call = p.parent.parent;
        if (
          name !== null && STATE_FIELDS.has(name) &&
          ts.isPropertyAccessExpression(init) && init.name.text === name &&
          ts.isObjectLiteralExpression(p.parent) && ts.isCallExpression(call) &&
          RENDER_SINKS.has(calleeName(call) ?? "") && call.arguments.some((a) => a === p.parent)
        ) {
          return;
        }
        // 2. senaryo kaydetme isteğinin observed_streak_user alanı
        if (name === "observed_streak_user" && enclosingFunctionName(p) === "save") return;
      }
      if (ts.isBinaryExpression(p) && p.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && p.operatorToken.kind <= ts.SyntaxKind.LastAssignment) {
        // 1. beyan işleyicisinde beyan durumunun kendisine atama
        if (isDeclTarget(p.left) && inHandlerCase(p)) return;
        if (cur === p.right && ts.isIdentifier(p.left)) return taintVar(p.left.text, p, origin);
        return report(start, `${origin}: beyan bir duruma atanıyor (${p.left.getText(sf)})`);
      }
      if (ts.isVariableDeclaration(p) && cur === p.initializer) {
        if (ts.isIdentifier(p.name)) return taintVar(p.name.text, p, origin);
        return report(start, `${origin}: yapı çözümlemeli atama`);
      }
      if (ts.isFunctionLike(p)) return report(start, `${origin}: fonksiyon sınırı (${ts.SyntaxKind[p.kind]})`);
      if (ts.isStatement(p) || ts.isCaseClause(p)) return report(start, `${origin}: ${ts.SyntaxKind[p.kind]} içinde kullanılıyor`);
      cur = p;
    }
  }

  const visit = (n: ts.Node) => {
    if (ts.isImportDeclaration(n)) return;
    if (ts.isIdentifier(n) && DECL_IDS.has(n.text)) follow(n, n.text);
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return out;
}
