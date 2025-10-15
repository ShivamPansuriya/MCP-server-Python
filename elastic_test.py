"""
Comprehensive Test Suite for Field-Level Fuzziness and Threshold Validation

Test Data:
1. User ID 1: Jimmi Thakkar (technician, licensing@zyduslife.com, 9586345111)
2. User ID 69: Gourab Mishra (requester, Gourab.Mishra@ZydusLife.com, 8359075780, userlogonname: 102619)
"""

import asyncio
from search_users_tool import search_users
import json
from user_type_enum import UserType
from elasticsearch_config_loader import get_config_loader


def print_test_header(test_name: str):
    """Print formatted test header."""
    print("\n" + "=" * 80)
    print(f"TEST: {test_name}")
    print("=" * 80)


def print_results(results: dict, test_description: str = ""):
    """Print formatted test results."""
    if test_description:
        print(f"\n{test_description}")
    print("-" * 80)

    if isinstance(results, dict) and "error" in results:
        print(f"❌ ERROR: {results['error']}")
        return

    if isinstance(results, dict) and "users" in results:
        users = results["users"]
        print(f"✅ Found {len(users)} user(s)")
        for i, user in enumerate(users, 1):
            print(f"\n  User {i}:")
            print(f"    ID: {user.get('id', 'N/A')}")
            print(f"    Name: {user.get('name', 'N/A')}")
            print(f"    Email: {user.get('email', 'N/A')}")
            print(f"    Contact: {user.get('contact', 'N/A')}")
            print(f"    Logon Name: {user.get('userlogonname', 'N/A')}")
            print(f"    User Type: {user.get('userType', 'N/A')}")
            print(f"    Score: {user.get('_score', 'N/A')}")
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))


async def test_1_exact_name_match():
    """Test 1: Exact name match - should work with any fuzziness."""
    print_test_header("Test 1: Exact Name Match")

    result = await search_users(name="Jimmi Thakkar")
    print_results(result, "Searching for exact name: 'Jimmi Thakkar'")


async def test_2_typo_in_name():
    """Test 2: Name with typo - tests fuzziness for user_name field."""
    print_test_header("Test 2: Name with Typo (Fuzziness Test)")

    # Test with 1 typo: "Jimmi" -> "Jimi" (missing one 'm')
    result = await search_users(name="Jimi Thakkar")
    print_results(result, "Searching with typo: 'Jimi Thakkar' (should match if fuzziness >= 1)")

    # Test with 2 typos: "Jimmi" -> "Jimi", "Thakkar" -> "Thakar"
    result2 = await search_users(name="Jimi Thakar")
    print_results(result2, "Searching with 2 typos: 'Jimi Thakar' (should match if fuzziness >= 2)")


async def test_3_exact_email_match():
    """Test 3: Exact email match."""
    print_test_header("Test 3: Exact Email Match")

    result = await search_users(email="licensing@zyduslife.com")
    print_results(result, "Searching for exact email: 'licensing@zyduslife.com'")


async def test_4_typo_in_email():
    """Test 4: Email with typo - should NOT match if email fuzziness=0."""
    print_test_header("Test 4: Email with Typo (Strict Matching Test)")

    # Test with typo in email: "licensing" -> "licencing" (typo)
    result = await search_users(email="licencing@zyduslife.com")
    print_results(result, "Searching with email typo: 'licencing@zyduslife.com' (should NOT match if fuzziness=0)")


async def test_5_partial_email():
    """Test 5: Partial email search."""
    print_test_header("Test 5: Partial Email Search")

    result = await search_users(email="licensing")
    print_results(result, "Searching for partial email: 'licensing'")


async def test_6_exact_contact():
    """Test 6: Exact contact number match."""
    print_test_header("Test 6: Exact Contact Number")

    result = await search_users(contact="9586345111")
    print_results(result, "Searching for exact contact: '9586345111'")


async def test_7_contact_with_typo():
    """Test 7: Contact with typo - tests fuzziness for contact field."""
    print_test_header("Test 7: Contact with Typo")

    # Typo in contact: "9586345111" -> "9586345112" (last digit wrong)
    result = await search_users(contact="9586345112")
    print_results(result, "Searching with contact typo: '9586345112' (should match if fuzziness >= 1)")


async def test_8_userlogonname_exact():
    """Test 8: Exact userlogonname match."""
    print_test_header("Test 8: Exact User Logon Name")

    result = await search_users(userlogonname="102619")
    print_results(result, "Searching for exact userlogonname: '102619'")


async def test_9_userlogonname_typo():
    """Test 9: Userlogonname with typo."""
    print_test_header("Test 9: User Logon Name with Typo")

    # Typo: "102619" -> "102618" (last digit wrong)
    result = await search_users(userlogonname="102618")
    print_results(result, "Searching with userlogonname typo: '102618' (should match if fuzziness >= 1)")


async def test_10_multi_field_search():
    """Test 10: Multi-field search with exact values."""
    print_test_header("Test 10: Multi-Field Search (Exact)")

    result = await search_users(
        name="Gourab Mishra",
        email="Gourab.Mishra@ZydusLife.com",
        contact="8359075780"
    )
    print_results(result, "Searching with name + email + contact (all exact)")


async def test_11_multi_field_with_typos():
    """Test 11: Multi-field search with typos in different fields."""
    print_test_header("Test 11: Multi-Field Search with Typos")

    result = await search_users(
        name="Gourab Misra",  # Typo: "Mishra" -> "Misra"
        email="Gourab.Mishra@ZydusLife.com",  # Exact
        contact="8359075780"  # Exact
    )
    print_results(result, "Searching with typo in name, exact email and contact")


async def test_12_user_type_filter():
    """Test 12: User type filtering."""
    print_test_header("Test 12: User Type Filtering")

    # Search for technician
    result1 = await search_users(name="Jimmi Thakkar", userType=UserType.TECHNICIAN)
    print_results(result1, "Searching 'Jimmi Thakkar' with userType=TECHNICIAN")

    # Search for requester (should not match Jimmi who is technician)
    result2 = await search_users(name="Jimmi Thakkar", userType=UserType.REQUESTER)
    print_results(result2, "Searching 'Jimmi Thakkar' with userType=REQUESTER (should NOT match)")


async def test_13_case_sensitivity():
    """Test 13: Case sensitivity test."""
    print_test_header("Test 13: Case Sensitivity")

    # Lowercase name
    result1 = await search_users(name="jimmi thakkar")
    print_results(result1, "Searching with lowercase: 'jimmi thakkar'")

    # Uppercase name
    result2 = await search_users(name="JIMMI THAKKAR")
    print_results(result2, "Searching with uppercase: 'JIMMI THAKKAR'")


async def test_14_config_validation():
    """Test 14: Validate configuration is loaded correctly."""
    print_test_header("Test 14: Configuration Validation")

    config_loader = get_config_loader()
    config = config_loader.get_config()

    print(f"\n📋 Configuration Summary:")
    print(f"  Global Fuzziness: {config.fuzziness}")
    print(f"  Global Min Score: {config.min_score}")
    print(f"  Default Limit: {config.default_limit}")
    print(f"  Max Limit: {config.max_limit}")
    print(f"\n📊 Field Configurations:")

    for field in config.get_enabled_fields():
        print(f"\n  Field: {field.name}")
        print(f"    Boost: {field.boost}")
        print(f"    Enabled: {field.enabled}")
        print(f"    Field Fuzziness: {field.fuzziness if field.fuzziness else 'Uses Global'}")
        print(f"    Field Min Score: {field.min_score if field.min_score else 'Uses Global'}")
        print(f"    Description: {field.description}")


async def run_all_tests():
    """Run all test cases."""
    print("\n" + "🚀" * 40)
    print("FIELD-LEVEL FUZZINESS & THRESHOLD VALIDATION TEST SUITE")
    print("🚀" * 40)

    # Configuration validation first
    await test_14_config_validation()

    # Basic exact match tests
    await test_1_exact_name_match()
    await test_3_exact_email_match()
    await test_6_exact_contact()
    await test_8_userlogonname_exact()

    # Fuzziness tests
    await test_2_typo_in_name()
    await test_4_typo_in_email()
    await test_7_contact_with_typo()
    await test_9_userlogonname_typo()

    # Multi-field tests
    await test_10_multi_field_search()
    await test_11_multi_field_with_typos()

    # Filter tests
    await test_12_user_type_filter()
    await test_13_case_sensitivity()

    # Partial match test
    await test_5_partial_email()

    print("\n" + "✅" * 40)
    print("ALL TESTS COMPLETED")
    print("✅" * 40 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
