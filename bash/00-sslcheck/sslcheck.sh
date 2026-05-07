#!/usr/bin/env bash

# sslcheck.sh
# Usage:
#   ./sslcheck.sh example.com
#   ./sslcheck.sh example.com 443
#   ./sslcheck.sh https://example.com:443

TIMEOUT_SEC="${TIMEOUT_SEC:-6}"
SCAN_CIPHERS="${SCAN_CIPHERS:-1}"

if [[ -z "$1" ]]; then
    echo "Usage: $0 <host|url> [port] [sni]"
    exit 1
fi

TARGET="$1"
TARGET="${TARGET#http://}"
TARGET="${TARGET#https://}"
TARGET="${TARGET%%/*}"

if [[ "$TARGET" == *:* ]]; then
    HOST="${TARGET%%:*}"
    PORT="${TARGET##*:}"
else
    HOST="$TARGET"
    PORT="${2:-443}"
fi

SNI="${3:-$HOST}"

if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl not found"
    exit 1
fi

if [[ -t 1 ]]; then
    RED="\033[31m"
    GREEN="\033[32m"
    YELLOW="\033[33m"
    CYAN="\033[36m"
    BOLD="\033[1m"
    RESET="\033[0m"
else
    RED=""
    GREEN=""
    YELLOW=""
    CYAN=""
    BOLD=""
    RESET=""
fi

sclient() {
    if command -v timeout >/dev/null 2>&1; then
        timeout "$TIMEOUT_SEC" openssl s_client \
            -connect "${HOST}:${PORT}" \
            -servername "$SNI" \
            "$@" < /dev/null 2>&1
    else
        openssl s_client \
            -connect "${HOST}:${PORT}" \
            -servername "$SNI" \
            "$@" < /dev/null 2>&1
    fi
}

has_sclient_option() {
    openssl s_client -help 2>&1 | grep -q -- "$1"
}

parse_cipher() {
    awk -F': *' '
        /^[[:space:]]*Cipher[[:space:]]*:/ {
            if ($2 != "" && $2 != "0000" && $2 != "(NONE)") {
                print $2
                exit
            }
        }
        /Cipher is/ {
            if ($0 !~ /Cipher is \(NONE\)/) {
                sub(/^.*Cipher is /, "")
                print
                exit
            }
        }
    '
}

parse_protocol() {
    awk -F': *' '
        /^[[:space:]]*Protocol[[:space:]]*:/ {
            print $2
            exit
        }
    '
}

parse_temp_key() {
    awk -F': *' '
        /Server Temp Key/ {
            print $2
            exit
        }
    '
}

cipher_bits() {
    local c="$1"

    case "$c" in
        *CHACHA20*) echo "256" ;;
        *AES256*|*AES_256*) echo "256" ;;
        *AES128*|*AES_128*) echo "128" ;;
        *3DES*|*DES-CBC3*) echo "112" ;;
        *RC4-128*) echo "128" ;;
        *RC4-40*) echo "40" ;;
        *CAMELLIA256*) echo "256" ;;
        *CAMELLIA128*) echo "128" ;;
        *ARIA256*) echo "256" ;;
        *ARIA128*) echo "128" ;;
        *) echo "?" ;;
    esac
}

resolve_ip() {
    local ip=""

    if command -v getent >/dev/null 2>&1; then
        ip="$(getent ahosts "$HOST" 2>/dev/null | awk '{print $1; exit}')"
    fi

    if [[ -z "$ip" ]] && command -v dig >/dev/null 2>&1; then
        ip="$(dig +short "$HOST" A 2>/dev/null | head -n1)"
    fi

    if [[ -z "$ip" ]] && command -v nslookup >/dev/null 2>&1; then
        ip="$(nslookup "$HOST" 2>/dev/null | awk '/^Address: / {print $2; exit}')"
    fi

    echo "${ip:-unknown}"
}

print_status() {
    local name="$1"
    local status="$2"

    if [[ "$status" == "enabled" ]]; then
        printf "%-8s ${GREEN}%s${RESET}\n" "$name" "$status"
    elif [[ "$status" == "disabled" ]]; then
        printf "%-8s ${RED}%s${RESET}\n" "$name" "$status"
    else
        printf "%-8s ${YELLOW}%s${RESET}\n" "$name" "$status"
    fi
}

declare -a PROTO_NAMES=(
    "SSLv2"
    "SSLv3"
    "TLSv1.0"
    "TLSv1.1"
    "TLSv1.2"
    "TLSv1.3"
)

declare -a PROTO_FLAGS=(
    "-ssl2"
    "-ssl3"
    "-tls1"
    "-tls1_1"
    "-tls1_2"
    "-tls1_3"
)

declare -A PROTO_STATUS
declare -A PROTO_OUTPUT

echo
echo "Version : ${GREEN}$(openssl version)${RESET}"
echo
echo "Connected to ${GREEN}$(resolve_ip)${RESET}"
echo
echo "Testing SSL server ${GREEN}${HOST}${RESET} on port ${GREEN}${PORT}${RESET} using SNI name ${GREEN}${SNI}${RESET}"
echo

echo -e "${CYAN}  SSL/TLS Protocols:${RESET}"

highest_enabled_index=-1

for i in "${!PROTO_NAMES[@]}"; do
    name="${PROTO_NAMES[$i]}"
    flag="${PROTO_FLAGS[$i]}"

    if ! has_sclient_option "$flag"; then
        PROTO_STATUS["$name"]="disabled"
        print_status "$name" "disabled"
        continue
    fi

    out="$(sclient "$flag" -cipher 'ALL:@SECLEVEL=0')"
    PROTO_OUTPUT["$name"]="$out"

    cipher="$(echo "$out" | parse_cipher)"

    if [[ -n "$cipher" ]]; then
        PROTO_STATUS["$name"]="enabled"
        highest_enabled_index="$i"
        print_status "$name" "enabled"
    else
        PROTO_STATUS["$name"]="disabled"
        print_status "$name" "disabled"
    fi
done

echo

echo -e "${CYAN}  TLS Fallback SCSV:${RESET}"

if ! has_sclient_option "-fallback_scsv"; then
    echo -e "Server ${YELLOW}unknown${RESET} TLS Fallback SCSV, local openssl does not support -fallback_scsv"
else
    if (( highest_enabled_index > 2 )); then
        fallback_index=$((highest_enabled_index - 1))
        fallback_flag="${PROTO_FLAGS[$fallback_index]}"

        out="$(sclient "$fallback_flag" -fallback_scsv -cipher 'ALL:@SECLEVEL=0')"

        if echo "$out" | grep -qi "inappropriate fallback"; then
            echo -e "Server ${GREEN}supports${RESET} TLS Fallback SCSV"
        else
            echo -e "Server ${YELLOW}does not confirm${RESET} TLS Fallback SCSV"
        fi
    else
        echo -e "Server ${YELLOW}unknown${RESET} TLS Fallback SCSV"
    fi
fi

echo

echo -e "${CYAN}  TLS renegotiation:${RESET}"

reneg_proto=""
reneg_flag=""

for p in "TLSv1.2" "TLSv1.1" "TLSv1.0"; do
    if [[ "${PROTO_STATUS[$p]}" == "enabled" ]]; then
        reneg_proto="$p"
        case "$p" in
            TLSv1.0) reneg_flag="-tls1" ;;
            TLSv1.1) reneg_flag="-tls1_1" ;;
            TLSv1.2) reneg_flag="-tls1_2" ;;
        esac
        break
    fi
done

if [[ -n "$reneg_flag" ]]; then
    out="$(sclient "$reneg_flag" -cipher 'ALL:@SECLEVEL=0')"

    if echo "$out" | grep -q "Secure Renegotiation IS supported"; then
        echo -e "${GREEN}Secure${RESET} session renegotiation supported"
    elif echo "$out" | grep -q "Secure Renegotiation IS NOT supported"; then
        echo -e "${RED}Insecure${RESET} session renegotiation not supported"
    else
        echo -e "${YELLOW}Unknown${RESET} renegotiation status"
    fi
else
    if [[ "${PROTO_STATUS[TLSv1.3]}" == "enabled" ]]; then
        echo -e "${GREEN}Not applicable${RESET}, TLS 1.3 does not use legacy renegotiation"
    else
        echo -e "${YELLOW}Unknown${RESET} renegotiation status"
    fi
fi

echo

echo -e "${CYAN}  TLS Compression:${RESET}"

comp_checked=0

for p in "TLSv1.2" "TLSv1.1" "TLSv1.0" "TLSv1.3"; do
    if [[ "${PROTO_STATUS[$p]}" == "enabled" ]]; then
        out="${PROTO_OUTPUT[$p]}"
        comp="$(echo "$out" | awk -F': *' '/^[[:space:]]*Compression[[:space:]]*:/ {print $2; exit}')"

        if [[ "$comp" == "NONE" || -z "$comp" ]]; then
            echo -e "Compression ${GREEN}disabled${RESET}"
        else
            echo -e "Compression ${RED}enabled${RESET}: $comp"
        fi

        comp_checked=1
        break
    fi
done

if [[ "$comp_checked" -eq 0 ]]; then
    echo -e "Compression ${YELLOW}unknown${RESET}"
fi

echo

echo -e "${CYAN}  Heartbleed:${RESET}"

for p in "TLSv1.3" "TLSv1.2" "TLSv1.1" "TLSv1.0"; do
    if [[ "${PROTO_STATUS[$p]}" != "enabled" ]]; then
        continue
    fi

    case "$p" in
        TLSv1.3)
            echo -e "$p ${GREEN}not vulnerable${RESET} to heartbleed"
            ;;
        TLSv1.2)
            out="$(sclient -tls1_2 -tlsextdebug -cipher 'ALL:@SECLEVEL=0')"
            if echo "$out" | grep -qi "heartbeat"; then
                echo -e "$p ${YELLOW}unknown${RESET}: heartbeat extension enabled, active probe required"
            else
                echo -e "$p ${GREEN}not vulnerable${RESET} to heartbleed"
            fi
            ;;
        TLSv1.1)
            out="$(sclient -tls1_1 -tlsextdebug -cipher 'ALL:@SECLEVEL=0')"
            if echo "$out" | grep -qi "heartbeat"; then
                echo -e "$p ${YELLOW}unknown${RESET}: heartbeat extension enabled, active probe required"
            else
                echo -e "$p ${GREEN}not vulnerable${RESET} to heartbleed"
            fi
            ;;
        TLSv1.0)
            out="$(sclient -tls1 -tlsextdebug -cipher 'ALL:@SECLEVEL=0')"
            if echo "$out" | grep -qi "heartbeat"; then
                echo -e "$p ${YELLOW}unknown${RESET}: heartbeat extension enabled, active probe required"
            else
                echo -e "$p ${GREEN}not vulnerable${RESET} to heartbleed"
            fi
            ;;
    esac
done

echo

echo -e "${CYAN}  Supported Server Cipher(s):${RESET}"

if [[ "$SCAN_CIPHERS" != "1" ]]; then
    echo "Cipher scan skipped. Set SCAN_CIPHERS=1 to enable."
    exit 0
fi

print_cipher_line() {
    local label="$1"
    local proto="$2"
    local cipher="$3"
    local tempkey="$4"
    local bits

    bits="$(cipher_bits "$cipher")"

    if [[ -n "$tempkey" ]]; then
        tempkey="  $tempkey"
    fi

    if [[ "$label" == "Preferred" ]]; then
        printf "${GREEN}%-9s${RESET} %-7s %4s bits  %-38s%s\n" "$label" "$proto" "$bits" "$cipher" "$tempkey"
    else
        printf "%-9s %-7s %4s bits  %-38s%s\n" "$label" "$proto" "$bits" "$cipher" "$tempkey"
    fi
}

get_preferred_cipher() {
    local proto="$1"
    local flag="$2"

    out="$(sclient "$flag" -cipher 'ALL:@SECLEVEL=0')"
    cipher="$(echo "$out" | parse_cipher)"
    tempkey="$(echo "$out" | parse_temp_key)"

    if [[ -n "$cipher" ]]; then
        print_cipher_line "Preferred" "$proto" "$cipher" "$tempkey"
    fi
}

test_cipher() {
    local proto="$1"
    local flag="$2"
    local cipher="$3"

    if [[ "$proto" == "TLSv1.3" ]]; then
        out="$(sclient "$flag" -ciphersuites "$cipher")"
    else
        out="$(sclient "$flag" -cipher "${cipher}:@SECLEVEL=0")"
    fi

    selected="$(echo "$out" | parse_cipher)"

    if [[ -n "$selected" ]]; then
        tempkey="$(echo "$out" | parse_temp_key)"
        print_cipher_line "Accepted" "$proto" "$selected" "$tempkey"
    fi
}

declare -a TLS13_CIPHERS=(
    "TLS_AES_256_GCM_SHA384"
    "TLS_CHACHA20_POLY1305_SHA256"
    "TLS_AES_128_GCM_SHA256"
    "TLS_AES_128_CCM_SHA256"
    "TLS_AES_128_CCM_8_SHA256"
)

mapfile -t LEGACY_CIPHERS < <(
    openssl ciphers 'ALL:@SECLEVEL=0' 2>/dev/null \
        | tr ':' '\n' \
        | grep -v '^TLS_' \
        | sort -u
)

for i in "${!PROTO_NAMES[@]}"; do
    proto="${PROTO_NAMES[$i]}"
    flag="${PROTO_FLAGS[$i]}"

    if [[ "${PROTO_STATUS[$proto]}" != "enabled" ]]; then
        continue
    fi

    get_preferred_cipher "$proto" "$flag"

    if [[ "$proto" == "TLSv1.3" ]]; then
        for c in "${TLS13_CIPHERS[@]}"; do
            test_cipher "$proto" "$flag" "$c"
        done
    elif [[ "$proto" == TLSv1.* ]]; then
        for c in "${LEGACY_CIPHERS[@]}"; do
            test_cipher "$proto" "$flag" "$c"
        done
    fi
done

echo
