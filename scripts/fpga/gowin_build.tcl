# Reproducible Gowin EDA CLI flow. Environment variables are set by build_gowin.ps1.
foreach required {PM25_PROJECT_ROOT PM25_GOWIN_DEVICE PM25_GOWIN_TOP PM25_GOWIN_FLOW} {
    if {![info exists ::env($required)] || $::env($required) eq ""} {
        error "Missing required environment variable: $required"
    }
}

set root [file normalize $::env(PM25_PROJECT_ROOT)]
set top $::env(PM25_GOWIN_TOP)
set flow $::env(PM25_GOWIN_FLOW)

foreach source {
    rtl/core/alert_classifier.v
    rtl/core/hysteresis.v
    rtl/core/bias_update.v
    rtl/core/fusion.v
    rtl/core/pm25_alert_core.v
} {
    add_file -type verilog [file join $root $source]
}

if {$top eq "pm25_uart_demo_top"} {
    foreach source {
        rtl/uart/uart_rx.v
        rtl/uart/uart_tx.v
        rtl/uart/pm25_packet_rx.v
        rtl/uart/pm25_packet_tx.v
        rtl/top/pm25_uart_demo_top.v
    } {
        add_file -type verilog [file join $root $source]
    }
    if {![info exists ::env(PM25_GOWIN_CST)] || $::env(PM25_GOWIN_CST) eq ""} {
        error "Full UART top requires PM25_GOWIN_CST with verified board pins."
    }
    add_file -type cst [file normalize $::env(PM25_GOWIN_CST)]
    if {[info exists ::env(PM25_GOWIN_SDC)] && $::env(PM25_GOWIN_SDC) ne ""} {
        add_file -type sdc [file normalize $::env(PM25_GOWIN_SDC)]
    }
}

set_device $::env(PM25_GOWIN_DEVICE)
set_option -top_module $top
set_option -include_path [file join $root rtl core]
set_option -verilog_std v2001
set_option -print_all_synthesis_warning 1
set_option -show_all_warn 1
run $flow
