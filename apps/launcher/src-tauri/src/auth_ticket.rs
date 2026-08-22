//! Trion 1.2/3.5 auth ticket — shared-memory SSO handshake.
//!
//! Port of the reference AAEmu-Launcher `Trion12Launcher.CreateTrinoHandleIDs`:
//! the launcher builds an XML auth ticket, RC4-encrypts it with a random key
//! and publishes it in a named file mapping plus a named event. The client
//! receives BOTH handles via `-handle <map>:<event>` and skips its own login
//! screen entirely (which also avoids the flaky login-UI init).
//!
//! Mapping contents layout: [8-byte RC4 key][i32 payload size][payload].

use std::os::windows::ffi::OsStrExt;

/// RC4 stream cipher (keystream XOR), as used by the original launcher.
fn rc4(key: &[u8], data: &[u8]) -> Vec<u8> {
    let mut s: [u8; 256] = core::array::from_fn(|i| i as u8);
    let mut j = 0usize;
    for i in 0..256 {
        j = (j + key[i % key.len()] as usize + s[i] as usize) & 255;
        s.swap(i, j);
    }
    let mut out = Vec::with_capacity(data.len());
    let (mut i, mut j) = (0usize, 0usize);
    for &b in data {
        i = (i + 1) & 255;
        j = (j + s[i] as usize) & 255;
        s.swap(i, j);
        out.push(b ^ s[(s[i].wrapping_add(s[j]) & 255) as usize]);
    }
    out
}

fn wide(s: &str) -> Vec<u16> {
    std::ffi::OsStr::new(s).encode_wide().chain(Some(0)).collect()
}

/// Builds the ticket payload and publishes it; returns (map_handle, event_handle)
/// as the numeric pair expected by `-handle XXXXXXXX:YYYYYYYY`.
/// `pass_sha256_hex` is the lowercase-hex SHA-256 of the raw password.
pub fn create_trino_ticket_hashed(user: &str, pass_sha256_hex: &str) -> Result<(u32, u32), String> {
    use windows_sys::Win32::Foundation::{CloseHandle, INVALID_HANDLE_VALUE};
    use windows_sys::Win32::Security::SECURITY_ATTRIBUTES;
    use windows_sys::Win32::System::Memory::{
        CreateFileMappingW, MapViewOfFile, UnmapViewOfFile, FILE_MAP_WRITE, PAGE_READWRITE,
    };
    use windows_sys::Win32::System::Threading::CreateEventW;

    // "TFIR" + base64("test") signature + newline + XML body (C# reference).
    let ticket = format!(
        "TFIRdGVzdA==\n<?xml version=\"1.0\" encoding=\"UTF - 8\" standalone=\"yes\"?>\
         <authTicket version = \"1.2\"><storeToken>1</storeToken>\
         <username>{user}</username><password>{pass_sha256_hex}</password></authTicket>"
    );
    let plain = ticket.as_bytes();

    let key: [u8; 8] = rand_key();
    let enc = rc4(&key, plain);

    let map_name = wide("archeage_auth_ticket_map");
    let evt_name = wide("archeage_auth_ticket_event");

    unsafe {
        let sa = SECURITY_ATTRIBUTES {
            nLength: std::mem::size_of::<SECURITY_ATTRIBUTES>() as u32,
            lpSecurityDescriptor: std::ptr::null_mut(),
            bInheritHandle: 1, // child must inherit both handles
        };

        let total = enc.len() + 0xC;
        let hmap = CreateFileMappingW(
            INVALID_HANDLE_VALUE,
            &sa,
            PAGE_READWRITE,
            0,
            total as u32,
            map_name.as_ptr(),
        );
        if hmap.is_null() {
            return Err("CreateFileMappingW failed".into());
        }
        let view = MapViewOfFile(hmap, FILE_MAP_WRITE, 0, 0, total);
        if view.Value.is_null() {
            CloseHandle(hmap);
            return Err("MapViewOfFile failed".into());
        }
        // [key(8)][size i32][encrypted]
        let dst = view.Value as *mut u8;
        std::ptr::copy_nonoverlapping(key.as_ptr(), dst, 8);
        std::ptr::copy_nonoverlapping((enc.len() as i32).to_le_bytes().as_ptr(), dst.add(8), 4);
        std::ptr::copy_nonoverlapping(enc.as_ptr(), dst.add(12), enc.len());
        UnmapViewOfFile(view);

        let hevt = CreateEventW(&sa, 1, 0, evt_name.as_ptr());
        if hevt.is_null() {
            CloseHandle(hmap);
            return Err("CreateEventW failed".into());
        }

        // Handle values fit in 32 bits in practice; the x86 client reads ints.
        Ok((hmap as usize as u32, hevt as usize as u32))
    }
}

/// Random 8-byte RC4 session key (xorshift seeded from time + address ASLR).
fn rand_key() -> [u8; 8] {
    use std::time::{SystemTime, UNIX_EPOCH};
    let t = SystemTime::now().duration_since(UNIX_EPOCH).unwrap();
    let mut seed =
        t.as_nanos() as u64 ^ (&rand_key as *const _ as u64) ^ (std::process::id() as u64) << 32;
    let mut out = [0u8; 8];
    for b in out.iter_mut() {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        *b = (seed & 0xFF) as u8;
    }
    out
}
