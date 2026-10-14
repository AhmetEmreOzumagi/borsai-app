// Port of app/tests/helpers.ts split() + wider arithmetic scan over app/src/**/*.ts
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
const SRC = process.argv[2];
function split(src){let code="";const strings=[];let i=0;const stack=[];let depth=0;
const readTemplate=()=>{let buf="";i+=1;while(i<src.length){const c=src[i];if(c==="\\"){buf+=src.slice(i,i+2);i+=2;}else if(c==="`"){i+=1;strings.push(buf);return;}else if(c==="$"&&src[i+1]==="{"){strings.push(buf);buf="";i+=2;stack.push(depth);depth+=1;code+=" ";return;}else{buf+=c;i+=1;}}};
while(i<src.length){const c=src[i],n=src[i+1];if(c==="/"&&n==="/"){while(i<src.length&&src[i]!=="\n")i+=1;}else if(c==="/"&&n==="*"){i=src.indexOf("*/",i+2)+2;}else if(c==="'"||c==='"'){let j=i+1;while(j<src.length&&src[j]!==c)j+=src[j]==="\\"?2:1;strings.push(src.slice(i+1,j));code+=" ";i=j+1;}else if(c==="`"){readTemplate();}else if(c==="}"&&stack.length&&depth-1===stack[stack.length-1]){stack.pop();depth-=1;readTemplate();}else{if(c==="{")depth+=1;if(c==="}")depth-=1;code+=c;i+=1;}}
return {code,strings};}
function walk(d){return readdirSync(d).flatMap(n=>{const p=join(d,n);return statSync(p).isDirectory()?walk(p):p.endsWith(".ts")?[p]:[];});}
const pats = {
  mulDivMod: /[^/*]\s*[*/%]\s*[^/*=]/,            // the project's op regex
  plusMinus: /(\w|\)|\])\s*[-+]\s*(\d|[A-Za-z_$][\w.$]*)\b/,
  math: /Math\.\w+/, toFixed: /toFixed|toPrecision/, numberCast: /\bNumber\(|parseFloat|parseInt/,
  reduce: /\.reduce\s*\(/, sortNum: /\.sort\s*\(\s*\(/, lengthShown: /\.length\b/,
};
for (const f of walk(SRC)) {
  const rel = f.slice(SRC.length+1);
  if (rel.startsWith("dev/")) continue;
  const { code } = split(readFileSync(f,"utf-8"));
  // keep line numbers: code preserves newlines (comments removed but \n kept? '//' loop stops at \n, kept; block comments drop newlines)
  const lines = code.split("\n");
  lines.forEach((l, idx) => {
    for (const [k, re] of Object.entries(pats)) {
      if (k==="lengthShown") continue;
      if (re.test(l) && !/^\s*import /.test(l)) {
        // exclude pure string concat lines for plusMinus
        if (k==="plusMinus" && !/[\w)\]]\s*[-+]\s*(\d|[A-Za-z_$])/.test(l.replace(/\s+\+\s+/g, " PLUS "))) continue;
        console.log(`${k}\t${rel}:${idx+1}\t${l.trim().slice(0,150)}`);
      }
    }
  });
}
