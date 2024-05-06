"""
module to handle the test generation and running of tests
"""
from .generator import TestGenerator
from .tester_utils import run_test, is_host_up, reduce_data_list
from .post_test_processor import PostRunTests
from .runner import TestRunner
from ..parsers.openapi import OpenAPIv3Parser
from ..parsers.swagger import SwaggerParser
from ..report.generator import ReportGenerator
from ..report.summary import ResultSummarizer
from ..logger import logger, console

# create tester obj
test_generator = TestGenerator()


# Note: redirects are allowed by default making it easier for pentesters/researchers
def generate_and_run_tests(
    api_parser: SwaggerParser | OpenAPIv3Parser,
    regex_pattern: str | None = None,
    output_file: str | None = None,
    output_file_format: str | None = None,
    rate_limit: int | None = None,
    req_headers: dict | None = None,
    proxies: list[str] | None = None,
    test_data_config: dict | None = None,
    ssl: bool = False,
    capture_failed: bool = False,
    remove_unused_data: bool = True,
):
    """
    Generates and runs tests for the provided OAS/Swagger file.

    Args:
        api_parser: An instance of SwaggerParser or OpenAPIv3Parser
        representing the parsed API specification.
        regex_pattern: A string representing the regex pattern to
        match against the response body (optional).
        output_file: A string representing the path to the output
        file (optional).
        output_file_format: A string representing the format of the
        output file (optional).
        rate_limit: An integer representing the rate limit for the
        tests (optional).
        req_headers: A dictionary representing the request headers
        (optional).
        proxies: A list of strings representing the proxies to be used
        (optional).
        test_data_config: A dictionary representing the configuration
        for user-provided test data (optional).
        ssl: A boolean indicating whether to use SSL for the requests
        (default: False).
        capture_failed: A boolean indicating whether to capture failed
        tests in the report (default: False).
        remove_unused_data: A boolean indicating whether to remove
        unused data (default: True).

    Returns:
        A list of test results.
    """
    if not is_host_up(openapi_parser=api_parser):
        logger.error(
            'Stopping tests due to unavailibility of host: %s', api_parser.host
        )
        return

    logger.info('Host %s is up', api_parser.host)

    test_runner = TestRunner(
        rate_limit=rate_limit,  # type: ignore
        headers=req_headers,
        proxies=proxies,
        ssl=ssl,
    )

    results: list = []

    # test for unsupported http methods
    test_name = 'Checking for Unsupported HTTP Methods/Verbs'
    logger.info(test_name)
    unsupported_http_endpoint_tests = test_generator.check_unsupported_http_methods(
        api_parser
    )

    results += run_test(
        test_runner=test_runner,
        tests=unsupported_http_endpoint_tests,
        regex_pattern=regex_pattern,
        description=f'(FUZZED) {test_name}',
    )

    # sqli fuzz test
    test_name = 'Checking for SQLi vulnerability'
    logger.info(test_name)
    sqli_fuzz_tests = test_generator.sqli_fuzz_params_test(api_parser)
    results += run_test(
        test_runner=test_runner,
        tests=sqli_fuzz_tests,
        regex_pattern=regex_pattern,
        description=f'(FUZZED) {test_name}',
    )

    test_name = 'Checking for SQLi vulnerability in URI Path'
    logger.info(test_name)
    sqli_fuzz_tests = test_generator.sqli_in_uri_path_fuzz_test(api_parser)
    results += run_test(
        test_runner=test_runner,
        tests=sqli_fuzz_tests,
        regex_pattern=regex_pattern,
        description=f'(FUZZED) {test_name}',
    )

    # OS Command Injection Fuzz Test
    test_name = 'Checking for OS Command Injection Vulnerability with fuzzed params and checking response body'  # noqa: E501
    logger.info(test_name)
    os_command_injection_tests = test_generator.os_command_injection_fuzz_params_test(
        api_parser
    )
    results += run_test(
        test_runner=test_runner,
        tests=os_command_injection_tests,
        regex_pattern=regex_pattern,
        post_run_matcher_test=True,
        description='(FUZZED) Checking for OS Command Injection',
    )

    # XSS/HTML Injection Fuzz Test
    test_name = 'Checking for XSS/HTML Injection Vulnerability with fuzzed params and checking response body'  # noqa: E501
    logger.info(test_name)
    xss_injection_tests = test_generator.xss_html_injection_fuzz_params_test(api_parser)
    results += run_test(
        test_runner=test_runner,
        tests=xss_injection_tests,
        regex_pattern=regex_pattern,
        post_run_matcher_test=True,
        description='(FUZZED) Checking for XSS/HTML Injection',
    )

    # BOLA path tests with fuzzed data
    test_name = 'Checking for BOLA in PATH using fuzzed params'
    logger.info(test_name)
    bola_fuzzed_path_tests = test_generator.bola_fuzz_path_test(
        api_parser, success_codes=[200, 201, 301]
    )
    results += run_test(
        test_runner=test_runner,
        tests=bola_fuzzed_path_tests,
        regex_pattern=regex_pattern,
        description='(FUZZED) Checking for BOLA in PATH:',
    )

    # BOLA path test with fuzzed data + trailing slash
    test_name = (
        'Checking for BOLA in PATH with trailing slash and id using fuzzed params'
    )
    logger.info(test_name)
    bola_trailing_slash_path_tests = test_generator.bola_fuzz_trailing_slash_path_test(
        api_parser, success_codes=[200, 201, 301]
    )
    results += run_test(
        test_runner=test_runner,
        tests=bola_trailing_slash_path_tests,
        regex_pattern=regex_pattern,
        description='(FUZZED) Checking for BOLA in PATH with trailing slash',
    )

    # Mass Assignment / BOPLA
    test_name = 'Checking for Mass Assignment Vulnerability with fuzzed params and checking response status codes:'  # noqa: E501
    logger.info(test_name)
    bopla_tests = test_generator.bopla_fuzz_test(
        api_parser, success_codes=[200, 201, 301]
    )
    results += run_test(
        test_runner=test_runner,
        tests=bopla_tests,
        regex_pattern=regex_pattern,
        description='(FUZZED) Checking for BOPLA/Mass Assignment Vulnerability',
    )

    # SSTI Vulnerability
    test_name = 'Checking for SSTI vulnerability with fuzzed params and checking response body'  # noqa: E501
    logger.info(test_name)
    ssti_tests = test_generator.ssti_fuzz_params_test(api_parser)
    results += run_test(
        test_runner=test_runner,
        tests=ssti_tests,
        regex_pattern=regex_pattern,
        description='(FUZZED) Checking for SSTI Vulnerability',
        post_run_matcher_test=True,
    )

    # Missing Authorization Test
    test_name = 'Checking for Missing Authorization'
    logger.info(test_name)
    missing_auth_tests = test_generator.missing_auth_fuzz_test(api_parser)
    results += run_test(
        test_runner=test_runner,
        tests=missing_auth_tests,
        regex_pattern=regex_pattern,
        description=f'(FUZZED) {test_name}',
        post_run_matcher_test=False,
    )

    # Tests with User provided Data
    if bool(test_data_config):
        logger.info('[bold] Testing with user provided data [/bold]')

        # # BOLA path tests with fuzzed + user provided data
        test_name = 'Checking for BOLA in PATH using fuzzed and user provided params'
        logger.info(test_name)
        bola_fuzzed_user_data_tests = test_generator.test_with_user_data(
            test_data_config,
            test_generator.bola_fuzz_path_test,
            openapi_parser=api_parser,
            success_codes=[200, 201, 301],
        )
        results += run_test(
            test_runner=test_runner,
            tests=bola_fuzzed_user_data_tests,
            regex_pattern=regex_pattern,
            description='(USER + FUZZED) Checking for BOLA in PATH',
        )

        # BOLA path test with fuzzed + user data + trailing slash
        test_name = 'Checking for BOLA in PATH with trailing slash id using fuzzed and user provided params:'  # noqa: E501
        logger.info(test_name)
        bola_trailing_slash_path_user_data_tests = test_generator.test_with_user_data(
            test_data_config,
            test_generator.bola_fuzz_trailing_slash_path_test,
            openapi_parser=api_parser,
            success_codes=[200, 201, 301],
        )
        results += run_test(
            test_runner=test_runner,
            tests=bola_trailing_slash_path_user_data_tests,
            regex_pattern=regex_pattern,
            description='(USER + FUZZED) Checking for BOLA in PATH with trailing slash',
        )

        # OS Command Injection Fuzz Test
        test_name = 'Checking for OS Command Injection Vulnerability with fuzzed & user params and checking response body'  # noqa: E501
        logger.info(test_name)
        os_command_injection_with_user_data_tests = test_generator.test_with_user_data(
            test_data_config,
            test_generator.os_command_injection_fuzz_params_test,
            openapi_parser=api_parser,
        )
        results += run_test(
            test_runner=test_runner,
            tests=os_command_injection_with_user_data_tests,
            regex_pattern=regex_pattern,
            post_run_matcher_test=True,
            description='(USER + FUZZED) Checking for OS Command Injection Vulnerability:',
        )

        # XSS/HTML Injection Fuzz Test
        test_name = 'Checking for XSS/HTML Injection Vulnerability with fuzzed & user params and checking response body'  # noqa: E501
        logger.info(test_name)
        os_command_injection_with_user_data_tests = test_generator.test_with_user_data(
            test_data_config,
            test_generator.xss_html_injection_fuzz_params_test,
            openapi_parser=api_parser,
        )
        results += run_test(
            test_runner=test_runner,
            tests=os_command_injection_with_user_data_tests,
            regex_pattern=regex_pattern,
            post_run_matcher_test=True,
            description='(USER + FUZZED) Checking for XSS/HTML Injection Vulnerability',
        )

        # STTI Vulnerability
        test_name = 'Checking for SSTI vulnerability with fuzzed params & user data and checking response body'  # noqa: E501
        logger.info(test_name)
        ssti_with_user_data_tests = test_generator.test_with_user_data(
            test_data_config,
            test_generator.ssti_fuzz_params_test,
            openapi_parser=api_parser,
        )
        results += run_test(
            test_runner=test_runner,
            tests=ssti_with_user_data_tests,
            regex_pattern=regex_pattern,
            description='(USER + FUZZED) Checking for SSTI Vulnerability',
            post_run_matcher_test=True,
        )

        # Missing Authorization Test
        test_name = 'Checking for Missing Authorization with user data'
        logger.info(test_name)
        missing_auth_tests = test_generator.test_with_user_data(
            test_data_config,
            test_generator.missing_auth_fuzz_test,
            openapi_parser=api_parser,
        )
        results += run_test(
            test_runner=test_runner,
            tests=missing_auth_tests,
            regex_pattern=regex_pattern,
            description=f'(USER + FUZZED) {test_name}',
            post_run_matcher_test=False,
        )

        # Broken Access Control Test
        test_name = 'Checking for Broken Access Control'
        logger.info(test_name)
        bac_results = PostRunTests.run_broken_access_control_tests(
            results, test_data_config
        )
        results += run_test(
            test_runner=test_runner,
            tests=bac_results,
            regex_pattern=regex_pattern,
            skip_test_run=True,
            description=test_name,
        )

    if remove_unused_data:
        for result in results:
            result.pop('kwargs', None)
            result.pop('args', None)

            result['body_params'] = reduce_data_list(result.get('body_params', [{}]))
            result['query_params'] = reduce_data_list(result.get('query_params', [{}]))
            result['path_params'] = reduce_data_list(result.get('path_params', [{}]))
            result['malicious_payload'] = reduce_data_list(
                result.get('malicious_payload', [])
            )

    # save file to output if output flag is present
    if output_file_format != 'table':
        ReportGenerator.generate_report(
            results=results,
            report_format=output_file_format,
            report_path=output_file,
            capture_failed=capture_failed,
        )

    ReportGenerator.generate_report(
        results=results,
        report_format='table',
        report_path=None,
        capture_failed=capture_failed,
    )

    console.print(
        "The columns for 'data_leak' and 'result' in the table represent independent aspects. It's possible for there to be a data leak in the endpoint, yet the result for that endpoint may still be marked as 'Success'. This is because the 'result' column doesn't necessarily reflect the overall test result; it may indicate success even in the presence of a data leak."
    )

    console.rule()
    result_summary = ResultSummarizer.generate_count_summary(
        results, table_title='Results Summary'
    )

    console.print(result_summary)

    return results
