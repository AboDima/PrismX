import asyncio
import copy
import os
import webbrowser

from asyncio_throttle import Throttler
from ScoutSuite import ERRORS_LIST

from concurrent.futures import ThreadPoolExecutor

from ScoutSuite.core.cli_parser import ScoutSuiteArgumentParser
from ScoutSuite.core.console import set_logger_configuration, print_info, print_exception
from ScoutSuite.core.exceptions import RuleExceptions
from ScoutSuite.core.processingengine import ProcessingEngine
from ScoutSuite.core.ruleset import Ruleset
from ScoutSuite.core.server import Server
from ScoutSuite.output.html import ScoutReport
from ScoutSuite.output.utils import get_filename
from ScoutSuite.providers import get_provider
from ScoutSuite.providers.base.authentication_strategy_factory import get_authentication_strategy


def run(provider,
        # AWS
        profile=None,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        # Azure
        user_account=False,
        user_account_browser=False,
        cli=False, msi=False, service_principal=False, file_auth=None,
        client_id=None, client_secret=None,
        username=None, password=None,
        tenant_id=None,
        subscription_ids=None, all_subscriptions=None,
        # GCP
        service_account=None,
        project_id=None, folder_id=None, organization_id=None, all_projects=False,
        # Aliyun
        access_key_id=None, access_key_secret=None,
        # General
        report_name=None, report_dir=None,
        timestamp=False,
        services=[], skipped_services=[], list_services=None,
        result_format='json',
        database_name=None, host_ip='127.0.0.1', host_port=8000,
        max_workers=10,
        regions=[],
        excluded_regions=[],
        fetch_local=False, update=False,
        max_rate=None,
        ip_ranges=[], ip_ranges_name_key='name',
        ruleset='default.json', exceptions=None,
        force_write=False,
        debug=False,
        quiet=False,
        log_file=None,
        no_browser=False,
        programmatic_execution=True):
    """
    Run a scout job in an async event loop.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Set the throttler within the loop so it's accessible later on
    loop.throttler = Throttler(rate_limit=max_rate if max_rate else 999999, period=1)
    loop.set_default_executor(ThreadPoolExecutor(max_workers=max_workers))
    result = loop.run_until_complete(_run(**locals()))  # pass through all the parameters
    loop.close()
    return result


async def _run(provider,
               # AWS
               profile,
               aws_access_key_id,
               aws_secret_access_key,
               aws_session_token,
               # Azure
               cli, user_account, user_account_browser,
               msi, service_principal, file_auth,
               tenant_id,
               subscription_ids, all_subscriptions,
               client_id, client_secret,
               username, password,
               # GCP
               service_account,
               project_id, folder_id, organization_id, all_projects,
               # Aliyun
               access_key_id, access_key_secret,
               # General
               report_name, report_dir,
               timestamp,
               services, skipped_services, list_services,
               result_format,
               database_name, host_ip, host_port,
               regions,
               excluded_regions,
               fetch_local, update,
               ip_ranges, ip_ranges_name_key,
               ruleset, exceptions,
               force_write,
               debug,
               quiet,
               log_file,
               no_browser,
               programmatic_execution,
               **kwargs):
    """
    Run a scout job.
    """

    # Configure the debug level
    set_logger_configuration(debug, quiet, log_file)

    print_info('Launching Scout')

    print_info('Authenticating to cloud provider')
    auth_strategy = get_authentication_strategy(provider)
    try:
        credentials = auth_strategy.authenticate(profile=profile,
                                                 aws_access_key_id=aws_access_key_id,
                                                 aws_secret_access_key=aws_secret_access_key,
                                                 aws_session_token=aws_session_token,
                                                 user_account=user_account,
                                                 user_account_browser=user_account_browser,
                                                 service_account=service_account,
                                                 cli=cli,
                                                 msi=msi,
                                                 service_principal=service_principal,
                                                 file_auth=file_auth,
                                                 tenant_id=tenant_id,
                                                 client_id=client_id,
                                                 client_secret=client_secret,
                                                 username=username,
                                                 password=password,
                                                 access_key_id=access_key_id,
                                                 access_key_secret=access_key_secret)

        if not credentials:
            return 101
    except Exception as e:
        print_exception('Authentication failure: {}'.format(e))
        return 101
    # Create a cloud provider object
    try:
        cloud_provider = get_provider(provider=provider,
                                      # AWS
                                      profile=profile,
                                      # Azure
                                      subscription_ids=subscription_ids,
                                      all_subscriptions=all_subscriptions,
                                      # GCP
                                      project_id=project_id,
                                      folder_id=folder_id,
                                      organization_id=organization_id,
                                      all_projects=all_projects,
                                      # Other
                                      report_dir=report_dir,
                                      timestamp=timestamp,
                                      services=services,
                                      skipped_services=skipped_services,
                                      programmatic_execution=programmatic_execution,
                                      credentials=credentials)
    except Exception as e:
        print_exception('Initialization failure: {}'.format(e))
        return 102

    # Create a new report
    report_name = report_name if report_name else cloud_provider.get_report_name()
    report = ScoutReport(cloud_provider.provider_code,
                         report_name,
                         report_dir,
                         timestamp,
                         result_format=result_format)

    if database_name:
        database_file, _ = get_filename('RESULTS', report_name, report_dir, file_extension="db")
        Server.init(database_file, host_ip, host_port)
        return

    # If this command, run and exit
    if list_services:
        available_services = [x for x in dir(cloud_provider.services) if
                              not (x.startswith('_') or x in ['credentials', 'fetch'])]
        print_info('The available services are: "{}"'.format('", "'.join(available_services)))
        return 0

    # Complete run, including pulling data from provider
    if not fetch_local:

        # Fetch data from provider APIs
        try:
            print_info('Gathering data from APIs')
            await cloud_provider.fetch(regions=regions, excluded_regions=excluded_regions)
        except KeyboardInterrupt:
            print_info('\nCancelled by user')
            return 130

        # Update means we reload the whole config and overwrite part of it
        if update:
            print_info('Updating existing data')
            current_run_services = copy.deepcopy(cloud_provider.services)
            last_run_dict = report.encoder.load_from_file('RESULTS')
            cloud_provider.services = last_run_dict['services']
            for service in cloud_provider.service_list:
                cloud_provider.services[service] = current_run_services[service]

    # Partial run, using pre-pulled data
    else:
        print_info('Using local data')
        # Reload to flatten everything into a python dictionary
        last_run_dict = report.encoder.load_from_file('RESULTS')
        for key in last_run_dict:
            setattr(cloud_provider, key, last_run_dict[key])

    # Pre processing
    cloud_provider.preprocessing(
        ip_ranges, ip_ranges_name_key)

    # Analyze config
    print_info('Running rule engine')
    finding_rules = Ruleset(cloud_provider=cloud_provider.provider_code,
                            environment_name=cloud_provider.environment,
                            filename=ruleset,
                            ip_ranges=ip_ranges,
                            account_id=cloud_provider.account_id)
    processing_engine = ProcessingEngine(finding_rules)
    processing_engine.run(cloud_provider)

    # Create display filters
    print_info('Applying display filters')
    filter_rules = Ruleset(cloud_provider=cloud_provider.provider_code,
                           environment_name=cloud_provider.environment,
                           filename='filters.json',
                           rule_type='filters',
                           account_id=cloud_provider.account_id)
    processing_engine = ProcessingEngine(filter_rules)
    processing_engine.run(cloud_provider)

    # Handle exceptions
    if exceptions:
        print_info('Applying exceptions')
        try:
            exceptions = RuleExceptions(exceptions)
            exceptions.process(cloud_provider)
            exceptions = exceptions.exceptions
        except Exception as e:
            print_exception('Failed to load exceptions: {}'.format(e))
            exceptions = {}
    else:
        exceptions = {}

    run_parameters = {
        'services': services,
        'skipped_services': skipped_services,
        'regions': regions,
        'excluded_regions': excluded_regions,
    }
    # Finalize
    cloud_provider.postprocessing(report.current_time, finding_rules, run_parameters)

    report.write(cloud_provider)


    if ERRORS_LIST:  # errors were handled during execution
        return 200
    else:
        return 0


