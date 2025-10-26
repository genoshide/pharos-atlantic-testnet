import random as _r

def _gen_ua():
    chrome_versions = ['110.0.0.0', '111.0.0.0', '112.0.0.0', '113.0.0.0', '114.0.0.0', '115.0.0.0', '116.0.0.0', '117.0.0.0', '118.0.0.0', '119.0.0.0', '120.0.0.0', '121.0.0.0', '122.0.0.0', '123.0.0.0', '124.0.0.0', '125.0.0.0']
    firefox_versions = ['110.0', '111.0', '112.0', '113.0', '114.0', '115.0', '116.0', '117.0', '118.0', '119.0', '120.0', '121.0', '122.0', '123.0', '124.0', '125.0']
    safari_versions = ['15.0', '15.1', '15.2', '15.3', '15.4', '15.5', '15.6', '16.0', '16.1', '16.2', '16.3', '16.4', '16.5', '17.0']
    edge_versions = ['110.0.0.0', '111.0.0.0', '112.0.0.0', '113.0.0.0', '114.0.0.0', '115.0.0.0', '116.0.0.0', '117.0.0.0', '118.0.0.0', '119.0.0.0', '120.0.0.0', '121.0.0.0', '122.0.0.0', '123.0.0.0', '124.0.0.0', '125.0.0.0']
    
    windows_versions = ['10.0', '11.0']
    macos_versions = ['10_15_7', '11_0_0', '11_1_0', '11_2_0', '11_3_0', '11_4_0', '11_5_0', '11_6_0', '12_0_0', '12_1_0', '12_2_0', '12_3_0', '12_4_0', '12_5_0', '12_6_0', '13_0_0', '13_1_0', '13_2_0', '13_3_0', '13_4_0', '13_5_0', '14_0_0']
    linux_types = ['X11; Linux x86_64', 'X11; Ubuntu; Linux x86_64', 'X11; Fedora; Linux x86_64']

    browser_types = [
        lambda: f"Mozilla/5.0 (Windows NT {_r.choice(windows_versions)}; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_r.choice(chrome_versions)} Safari/537.36",
        lambda: f"Mozilla/5.0 (Macintosh; Intel Mac OS X {_r.choice(macos_versions)}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_r.choice(chrome_versions)} Safari/537.36",
        lambda: f"Mozilla/5.0 ({_r.choice(linux_types)}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_r.choice(chrome_versions)} Safari/537.36",
        lambda: f"Mozilla/5.0 (Windows NT {_r.choice(windows_versions)}; Win64; x64; rv:{_r.choice(firefox_versions)}) Gecko/20100101 Firefox/{_r.choice(firefox_versions)}",
        lambda: f"Mozilla/5.0 (Macintosh; Intel Mac OS X {_r.choice(macos_versions)}; rv:{_r.choice(firefox_versions)}) Gecko/20100101 Firefox/{_r.choice(firefox_versions)}",
        lambda: f"Mozilla/5.0 (Macintosh; Intel Mac OS X {_r.choice(macos_versions)}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{_r.choice(safari_versions)} Safari/605.1.15",
        lambda: f"Mozilla/5.0 (Windows NT {_r.choice(windows_versions)}; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_r.choice(edge_versions)} Safari/537.36 Edg/{_r.choice(edge_versions)}",
    ]
    return _r.choice(browser_types)()