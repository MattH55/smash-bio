//! Hand-written JSON: a tiny reader for engine input, a strict writer for
//! engine output. No serde (see Cargo.toml: the crate has zero dependencies).

/// Escape a string for JSON output. Control characters become \u00XX so the
/// output is always valid for JSON.parse, including fetched source snippets.
pub fn quote(s: &str) -> String {
    let mut o = String::with_capacity(s.len() + 2);
    o.push('"');
    for c in s.chars() {
        match c {
            '"' => o.push_str("\\\""),
            '\\' => o.push_str("\\\\"),
            '\n' => o.push_str("\\n"),
            '\r' => o.push_str("\\r"),
            '\t' => o.push_str("\\t"),
            c if (c as u32) < 0x20 => o.push_str(&format!("\\u{:04x}", c as u32)),
            c => o.push(c),
        }
    }
    o.push('"');
    o
}

/// Finite floats only: JSON has no NaN/Infinity, and emitting `null` for a
/// diverged run is more honest than emitting an invalid token.
pub fn num(v: f64) -> String {
    if !v.is_finite() {
        return "null".to_string();
    }
    if v == 0.0 {
        return "0".to_string();
    }
    let a = v.abs();
    if a >= 1e15 || a < 1e-5 {
        return format!("{:e}", v);
    }
    // 12 significant digits: full f64 detail is below the model's own
    // uncertainty, and trailing garbage makes CSV/JSON diffs noisy.
    let mut t = format!("{:.12}", v);
    while t.contains('.') && (t.ends_with('0') || t.ends_with('.')) {
        t.pop();
    }
    t
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JsonErr(pub String);

impl std::fmt::Display for JsonErr {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[derive(Debug, Clone)]
pub enum Json {
    Null,
    Bool(bool),
    Num(f64),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(String, Json)>),
}

impl Json {
    pub fn get(&self, key: &str) -> Option<&Json> {
        if let Json::Obj(kvs) = self {
            kvs.iter().find(|(k, _)| k == key).map(|(_, v)| v)
        } else {
            None
        }
    }
    pub fn as_str(&self) -> Option<&str> {
        if let Json::Str(s) = self { Some(s) } else { None }
    }
    pub fn as_arr(&self) -> Option<&[Json]> {
        if let Json::Arr(a) = self { Some(a) } else { None }
    }
    pub fn as_f64(&self) -> Option<f64> {
        match self {
            Json::Num(v) => Some(*v),
            Json::Str(s) => s.trim().parse::<f64>().ok(),
            _ => None,
        }
    }
    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Json::Bool(b) => Some(*b),
            Json::Str(s) => match s.trim().to_ascii_lowercase().as_str() {
                "true" | "1" | "yes" | "on" => Some(true),
                "false" | "0" | "no" | "off" => Some(false),
                _ => None,
            },
            Json::Num(v) => Some(*v != 0.0),
            _ => None,
        }
    }
    pub fn f64_at(&self, key: &str, def: f64) -> f64 {
        self.get(key).and_then(|v| v.as_f64()).unwrap_or(def)
    }
    pub fn str_at(&self, key: &str, def: &str) -> String {
        self.get(key)
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
            .unwrap_or_else(|| def.to_string())
    }
    pub fn bool_at(&self, key: &str, def: bool) -> bool {
        self.get(key).and_then(|v| v.as_bool()).unwrap_or(def)
    }
}


pub fn parse(src: &str) -> Result<Json, JsonErr> {
    let b = src.as_bytes();
    let mut i = 0usize;
    skip_ws(b, &mut i);
    let v = value(b, &mut i)?;
    skip_ws(b, &mut i);
    if i != b.len() {
        return Err(JsonErr(format!("trailing content at byte {}", i)));
    }
    Ok(v)
}

fn skip_ws(b: &[u8], i: &mut usize) {
    while *i < b.len() && matches!(b[*i], b' ' | b'\t' | b'\n' | b'\r') {
        *i += 1;
    }
}

fn lit(b: &[u8], i: &mut usize, word: &str, v: Json) -> Result<Json, JsonErr> {
    if b.len() >= *i + word.len() && &b[*i..*i + word.len()] == word.as_bytes() {
        *i += word.len();
        Ok(v)
    } else {
        Err(JsonErr(format!("bad literal at {}", *i)))
    }
}

fn num_tok(b: &[u8], i: &mut usize) -> Result<Json, JsonErr> {
    let start = *i;
    while *i < b.len()
        && (b[*i].is_ascii_digit() || matches!(b[*i], b'-' | b'+' | b'.' | b'e' | b'E'))
    {
        *i += 1;
    }
    let s = std::str::from_utf8(&b[start..*i]).map_err(|_| JsonErr("bad utf8 number".into()))?;
    s.parse::<f64>()
        .map(Json::Num)
        .map_err(|_| JsonErr(format!("bad number {:?}", s)))
}

fn str_tok(b: &[u8], i: &mut usize) -> Result<String, JsonErr> {
    *i += 1;
    let mut out = String::new();
    loop {
        if *i >= b.len() {
            return Err(JsonErr("unterminated string".into()));
        }
        match b[*i] {
            b'"' => {
                *i += 1;
                return Ok(out);
            }
            b'\\' => {
                *i += 1;
                if *i >= b.len() {
                    return Err(JsonErr("bad escape".into()));
                }
                let c = match b[*i] {
                    b'n' => '\n',
                    b'r' => '\r',
                    b't' => '\t',
                    b'"' => '"',
                    b'\\' => '\\',
                    b'/' => '/',
                    b'b' => '\u{8}',
                    b'f' => '\u{c}',
                    b'u' => {
                        if *i + 4 >= b.len() {
                            return Err(JsonErr("bad \\u escape".into()));
                        }
                        let hex = std::str::from_utf8(&b[*i + 1..*i + 5])
                            .map_err(|_| JsonErr("bad \\u hex".into()))?;
                        let cp =
                            u32::from_str_radix(hex, 16).map_err(|_| JsonErr("bad \\u".into()))?;
                        *i += 4;
                        char::from_u32(cp).unwrap_or('\u{fffd}')
                    }
                    other => return Err(JsonErr(format!("bad escape \\{}", other as char))),
                };
                out.push(c);
                *i += 1;
            }
            _ => {
                // Copy the whole run up to the next quote or backslash in one go.
                // Both are ASCII and never occur inside a multi-byte UTF-8
                // sequence, so the run is valid UTF-8 on its own. (Decoding
                // from `&b[*i..]` per character was quadratic: a 3 MB PDB
                // string took minutes.)
                let start = *i;
                while *i < b.len() && b[*i] != b'"' && b[*i] != b'\\' {
                    *i += 1;
                }
                let s = std::str::from_utf8(&b[start..*i]).map_err(|_| JsonErr("bad utf8".into()))?;
                out.push_str(s);
            }
        }
    }
}

fn value(b: &[u8], i: &mut usize) -> Result<Json, JsonErr> {
    if *i >= b.len() {
        return Err(JsonErr("unexpected end of input".into()));
    }
    match b[*i] {
        b'{' => {
            *i += 1;
            let mut out: Vec<(String, Json)> = Vec::new();
            skip_ws(b, i);
            if *i < b.len() && b[*i] == b'}' {
                *i += 1;
                return Ok(Json::Obj(out));
            }
            loop {
                skip_ws(b, i);
                let key = match value(b, i)? {
                    Json::Str(s) => s,
                    _ => return Err(JsonErr("object key must be string".into())),
                };
                skip_ws(b, i);
                if *i >= b.len() || b[*i] != b':' {
                    return Err(JsonErr(format!("expected ':' after key at {}", *i)));
                }
                *i += 1;
                skip_ws(b, i);
                let v = value(b, i)?;
                out.push((key, v));
                skip_ws(b, i);
                if *i < b.len() && b[*i] == b',' {
                    *i += 1;
                    continue;
                }
                if *i < b.len() && b[*i] == b'}' {
                    *i += 1;
                    return Ok(Json::Obj(out));
                }
                return Err(JsonErr(format!("expected ',' or '}}' at {}", *i)));
            }
        }
        b'[' => {
            *i += 1;
            let mut out: Vec<Json> = Vec::new();
            skip_ws(b, i);
            if *i < b.len() && b[*i] == b']' {
                *i += 1;
                return Ok(Json::Arr(out));
            }
            loop {
                skip_ws(b, i);
                out.push(value(b, i)?);
                skip_ws(b, i);
                if *i < b.len() && b[*i] == b',' {
                    *i += 1;
                    continue;
                }
                if *i < b.len() && b[*i] == b']' {
                    *i += 1;
                    return Ok(Json::Arr(out));
                }
                return Err(JsonErr(format!("expected ',' or ']' at {}", *i)));
            }
        }
        b'"' => str_tok(b, i).map(Json::Str),
        b't' => lit(b, i, "true", Json::Bool(true)),
        b'f' => lit(b, i, "false", Json::Bool(false)),
        b'n' => lit(b, i, "null", Json::Null),
        c if c == b'-' || c.is_ascii_digit() => num_tok(b, i),
        c => Err(JsonErr(format!("unexpected byte {:?} at {}", c as char, *i))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn read_roundtrip() {
        let j = parse(r#"{"a":1.5,"b":"x\ny","c":[true,null,{"d":false}]}"#).unwrap();
        assert_eq!(j.f64_at("a", 0.0), 1.5);
        assert_eq!(j.str_at("b", ""), "x\ny");
        let arr = j.get("c").unwrap().as_arr().unwrap();
        assert_eq!(arr.len(), 3);
        assert_eq!(arr[2].get("d").unwrap().as_bool(), Some(false));
    }

    #[test]
    fn bad_json_is_an_error_not_a_panic() {
        for s in ["{\"a\":", "[1,", "nope", "{\"a\" 1}", "1 2", "\"\\q\""] {
            assert!(parse(s).is_err(), "should fail: {}", s);
        }
        assert!(parse("{}").is_ok());
        assert!(parse("  \n [ ] ").is_ok());
    }

    #[test]
    fn long_strings_parse_in_linear_time() {
        let body = "ATOM  é\u{3b1}x\n".repeat(400_000); // ~4.4 MB with multi-byte chars
        let src = format!("{{\"pdb\":{}}}", quote(&body));
        let t = std::time::Instant::now();
        let j = parse(&src).unwrap();
        assert_eq!(j.str_at("pdb", ""), body);
        assert!(t.elapsed().as_secs_f64() < 2.0, "took {:?}", t.elapsed());
    }

    #[test]
    fn num_output_is_json_safe() {
        assert_eq!(num(1.5), "1.5");
        assert_eq!(num(100.0), "100");
        assert_eq!(num(0.0), "0");
        assert_eq!(num(f64::NAN), "null");
        assert_eq!(num(f64::INFINITY), "null");
        assert!(num(1e-9).contains('e'));
    }

    #[test]
    fn quote_escapes() {
        assert_eq!(quote("a\"b\\c\nd"), "\"a\\\"b\\\\c\\nd\"");
        assert_eq!(quote("\u{1}"), "\"\\u0001\"");
    }
}

