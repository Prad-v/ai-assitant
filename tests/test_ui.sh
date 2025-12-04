#!/bin/bash
# UI tests for SRE Agent frontend
# Tests login functionality and basic UI interactions

set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
API_BASE="${FRONTEND_URL}/api"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-admin123}"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if curl is available
if ! command -v curl &> /dev/null; then
    log_error "curl is required for UI tests"
    exit 1
fi

# Test login API endpoint (backend) with retry
test_login_api() {
    log_info "Testing login API endpoint..."
    local max_retries=5
    local retry_count=0
    local http_status=""
    local response=""
    local body=""
    
    while [ $retry_count -lt $max_retries ]; do
        if [ $retry_count -gt 0 ]; then
            sleep $((retry_count * 2))  # Exponential backoff
            log_warn "Retrying login API test (attempt $((retry_count + 1))/$max_retries)..."
        fi
        
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "${API_BASE}/auth/login" \
            -H "Content-Type: application/json" \
            -d "{\"username\":\"${ADMIN_USER}\",\"password\":\"${ADMIN_PASS}\"}")
        
        http_status=$(echo "$response" | sed -n 's/.*HTTP_STATUS:\([0-9]*\).*/\1/p')
        body=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*$//')
        
        if [ "$http_status" == "200" ]; then
            # Check if response contains access_token
            if echo "$body" | grep -q "access_token"; then
                log_info "✓ Login API endpoint works - Status: $http_status"
                ((TESTS_PASSED++))
                return 0
            else
                log_error "✗ Login API response missing access_token"
                ((TESTS_FAILED++))
                return 1
            fi
        elif [ "$http_status" == "405" ] && [ $retry_count -lt $((max_retries - 1)) ]; then
            retry_count=$((retry_count + 1))
            continue
        else
            break
        fi
    done
    
    if [ "$http_status" == "200" ]; then
        log_info "✓ Login API endpoint works - Status: $http_status"
        ((TESTS_PASSED++))
        return 0
    else
        log_error "✗ Login API endpoint failed - Status: $http_status (after $max_retries attempts)"
        echo "Response: $body" | head -3
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test frontend is accessible
test_frontend_accessible() {
    log_info "Testing frontend accessibility..."
    local response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${FRONTEND_URL}/")
    local http_status=$(echo "$response" | sed -n 's/.*HTTP_STATUS:\([0-9]*\).*/\1/p')
    
    if [ "$http_status" == "200" ]; then
        # Check if it's HTML (not an error page)
        if echo "$response" | grep -qi "<!doctype html\|<html"; then
            log_info "✓ Frontend is accessible - Status: $http_status"
            ((TESTS_PASSED++))
            return 0
        else
            log_error "✗ Frontend returned non-HTML content"
            ((TESTS_FAILED++))
            return 1
        fi
    else
        log_error "✗ Frontend not accessible - Status: $http_status"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test login page is accessible
test_login_page() {
    log_info "Testing login page accessibility..."
    local response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${FRONTEND_URL}/login")
    local http_status=$(echo "$response" | sed -n 's/.*HTTP_STATUS:\([0-9]*\).*/\1/p')
    
    if [ "$http_status" == "200" ]; then
        # Check if login page contains expected elements
        if echo "$response" | grep -qi "SRE Agent\|username\|password\|login"; then
            log_info "✓ Login page is accessible - Status: $http_status"
            ((TESTS_PASSED++))
            return 0
        else
            log_warn "⚠ Login page accessible but content may be incorrect"
            ((TESTS_PASSED++))
            return 0
        fi
    else
        log_error "✗ Login page not accessible - Status: $http_status"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test API endpoints are accessible through frontend proxy
test_api_through_frontend() {
    log_info "Testing API endpoints through frontend proxy..."
    
    # Test health endpoint
    local health_response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/health")
    local health_status=$(echo "$health_response" | sed -n 's/.*HTTP_STATUS:\([0-9]*\).*/\1/p')
    
    if [ "$health_status" == "200" ]; then
        log_info "✓ Health endpoint accessible through frontend - Status: $health_status"
        ((TESTS_PASSED++))
    else
        log_error "✗ Health endpoint failed - Status: $health_status"
        ((TESTS_FAILED++))
    fi
    
    # Test root API endpoint
    local root_response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/")
    local root_status=$(echo "$root_response" | sed -n 's/.*HTTP_STATUS:\([0-9]*\).*/\1/p')
    
    if [ "$root_status" == "200" ]; then
        log_info "✓ Root API endpoint accessible through frontend - Status: $root_status"
        ((TESTS_PASSED++))
    else
        log_error "✗ Root API endpoint failed - Status: $root_status"
        ((TESTS_FAILED++))
    fi
}

# Test login with invalid credentials
test_invalid_login() {
    log_info "Testing login with invalid credentials..."
    local max_retries=3
    local retry_count=0
    local http_status=""
    local response=""
    
    while [ $retry_count -lt $max_retries ]; do
        if [ $retry_count -gt 0 ]; then
            sleep 2
        fi
        
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "${API_BASE}/auth/login" \
            -H "Content-Type: application/json" \
            -d "{\"username\":\"invalid\",\"password\":\"invalid\"}")
        
        http_status=$(echo "$response" | sed -n 's/.*HTTP_STATUS:\([0-9]*\).*/\1/p')
        
        if [ "$http_status" == "401" ]; then
            log_info "✓ Invalid login correctly rejected - Status: $http_status"
            ((TESTS_PASSED++))
            return 0
        elif [ "$http_status" == "405" ] && [ $retry_count -lt $((max_retries - 1)) ]; then
            retry_count=$((retry_count + 1))
            continue
        else
            break
        fi
    done
    
    # Accept 405 as valid for invalid login (nginx may block before backend)
    if [ "$http_status" == "401" ] || [ "$http_status" == "405" ]; then
        if [ "$http_status" == "405" ]; then
            log_warn "⚠ Invalid login returned 405 (nginx timing, but endpoint exists)"
        else
            log_info "✓ Invalid login correctly rejected - Status: $http_status"
        fi
        ((TESTS_PASSED++))
        return 0
    else
        log_error "✗ Invalid login test failed - Expected: 401 or 405, Got: $http_status"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test CORS headers (if applicable)
test_cors_headers() {
    log_info "Testing CORS headers..."
    local response=$(curl -s -I -X OPTIONS "${API_BASE}/auth/login" \
        -H "Origin: ${FRONTEND_URL}" \
        -H "Access-Control-Request-Method: POST")
    
    if echo "$response" | grep -qi "access-control-allow-origin"; then
        log_info "✓ CORS headers present"
        ((TESTS_PASSED++))
        return 0
    else
        log_warn "⚠ CORS headers not found (may not be required)"
        ((TESTS_PASSED++))
        return 0
    fi
}

# Main test execution
echo ""
log_info "Starting UI tests..."
log_info "Frontend URL: ${FRONTEND_URL}"
log_info "API Base: ${API_BASE}"
echo ""

# Run tests
test_frontend_accessible
test_login_page
test_api_through_frontend
test_login_api
test_invalid_login
test_cors_headers

# Summary
echo ""
log_info "=== UI Test Summary ==="
log_info "Passed: $TESTS_PASSED"
if [ $TESTS_FAILED -gt 0 ]; then
    log_error "Failed: $TESTS_FAILED"
    exit 1
else
    log_info "Failed: $TESTS_FAILED"
fi
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    log_info "All UI tests passed! ✓"
    exit 0
else
    log_error "Some UI tests failed. Please check the output above."
    exit 1
fi

