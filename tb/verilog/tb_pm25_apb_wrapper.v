`timescale 1ns/1ps

// Self-checking APB3 protocol and native-core equivalence regression.
module tb_pm25_apb_wrapper;

reg PCLK;
reg PRESETn;
reg PSEL;
reg PENABLE;
reg PWRITE;
reg [7:0] PADDR;
reg [31:0] PWDATA;
wire [31:0] PRDATA;
wire PREADY;
wire PSLVERR;

integer errors;
integer transactions;
integer checks;
integer reference_requests;
integer dut_core_requests;

reg ref_request_pulse;
reg ref_sample_valid;
reg ref_qc_ok;
reg [4:0] ref_hour;
reg signed [31:0] ref_cams_pm25_x16;
reg signed [31:0] ref_pa_pm25_x16;
reg expected_dut_request;

wire ref_result_valid;
wire ref_accepted;
wire signed [31:0] ref_fused_pm25_x16;
wire [2:0] ref_alert_level;
wire ref_alert_state_after;
wire signed [31:0] ref_bias_state_x16;

reg captured_ref_result_valid;
reg captured_ref_accepted;
reg [2:0] captured_ref_alert_level;
reg captured_ref_alert_state;
reg signed [31:0] captured_ref_fused_pm25_x16;
reg signed [31:0] captured_ref_bias_state_x16;

pm25_apb_wrapper #(
    .ALPHA_SHIFT(3),
    .PADDR_WIDTH(8)
) dut (
    .PCLK(PCLK),
    .PRESETn(PRESETn),
    .PSEL(PSEL),
    .PENABLE(PENABLE),
    .PWRITE(PWRITE),
    .PADDR(PADDR),
    .PWDATA(PWDATA),
    .PRDATA(PRDATA),
    .PREADY(PREADY),
    .PSLVERR(PSLVERR)
);

// Independent native-core instance.  Every logical payload below is owned by
// the testbench and is loaded from transaction intent before the APB PROCESS
// access.  No DUT snapshot, decode, or request signal drives this reference.
pm25_alert_core #(
    .ALPHA_SHIFT(3)
) reference_core (
    .clk(PCLK),
    .rst_n(PRESETn),
    .sample_valid(ref_request_pulse && ref_sample_valid),
    .qc_ok(ref_qc_ok),
    .hour(ref_hour),
    .cams_pm25_x16(ref_cams_pm25_x16),
    .pa_pm25_x16(ref_pa_pm25_x16),
    .sample_ready(),
    .result_valid(ref_result_valid),
    .accepted(ref_accepted),
    .hour_out(),
    .bias_before_x16(),
    .residual_x16(),
    .error_x16(),
    .delta_x16(),
    .bias_after_x16(),
    .fused_raw_x16(),
    .fused_pm25_x16(ref_fused_pm25_x16),
    .alert_level(ref_alert_level),
    .alert_state_before(),
    .alert_state_after(ref_alert_state_after),
    .bias_state_x16(ref_bias_state_x16)
);

initial PCLK = 1'b0;
always #5 PCLK = ~PCLK;

task check32;
    input [255:0] name;
    input [31:0] expected;
    input [31:0] actual;
    begin
        checks = checks + 1;
        if (actual !== expected) begin
            errors = errors + 1;
            $display("MISMATCH field=%0s expected=0x%08x actual=0x%08x",
                     name, expected, actual);
        end
    end
endtask

task capture_reference;
    begin
        captured_ref_result_valid = ref_result_valid;
        captured_ref_accepted = ref_accepted;
        captured_ref_alert_level = ref_alert_level;
        captured_ref_alert_state = ref_alert_state_after;
        captured_ref_fused_pm25_x16 = ref_fused_pm25_x16;
        captured_ref_bias_state_x16 = ref_bias_state_x16;
    end
endtask

// Observe the DUT request boundary without using it to drive the reference.
// These checks make address/register/snapshot/core wiring faults explicit,
// including HOUR, which does not otherwise affect an APB-visible result.
always @(posedge PCLK) begin
    if (!PRESETn) begin
        reference_requests = 0;
        dut_core_requests = 0;
        expected_dut_request = 1'b0;
    end else begin
        if (ref_request_pulse)
            reference_requests = reference_requests + 1;
        if (dut.core_request_pulse) begin
            dut_core_requests = dut_core_requests + 1;
            check32("expected_core_request", 32'd1,
                    {31'd0, expected_dut_request});
            check32("snapshot_sample_valid", {31'd0, ref_sample_valid},
                    {31'd0, dut.snapshot_sample_valid});
            check32("snapshot_qc_ok", {31'd0, ref_qc_ok},
                    {31'd0, dut.snapshot_qc_ok});
            check32("snapshot_hour", {27'd0, ref_hour},
                    {27'd0, dut.snapshot_hour});
            check32("snapshot_cams", ref_cams_pm25_x16,
                    dut.snapshot_cams_pm25_x16);
            check32("snapshot_pa", ref_pa_pm25_x16,
                    dut.snapshot_pa_pm25_x16);
            #1 check32("native_core_hour", {27'd0, ref_hour},
                       {27'd0, dut.u_core.hour_out});
            expected_dut_request = 1'b0;
        end
    end
end

task apb_idle;
    begin
        PSEL = 1'b0;
        PENABLE = 1'b0;
        PWRITE = 1'b0;
        PADDR = 8'd0;
        PWDATA = 32'd0;
    end
endtask

task apb_write;
    input [7:0] address;
    input [31:0] data;
    input expected_error;
    begin
        @(negedge PCLK);
        PSEL = 1'b1;
        PENABLE = 1'b0;
        PWRITE = 1'b1;
        PADDR = address;
        PWDATA = data;
        @(negedge PCLK);
        PENABLE = 1'b1;
        #1;
        check32("write_pready", 32'd1, {31'd0, PREADY});
        check32("write_pslverr", {31'd0, expected_error},
                {31'd0, PSLVERR});
        @(posedge PCLK);
        transactions = transactions + 1;
        @(negedge PCLK);
        apb_idle();
    end
endtask

// Issue PROCESS while independently presenting the intended transaction to
// the native reference core on the same acceptance edge.
task apb_process;
    input [31:0] control_data;
    input [31:0] intended_cams_x16;
    input [31:0] intended_pa_x16;
    input [4:0] intended_hour;
    begin
        @(negedge PCLK);
        PSEL = 1'b1;
        PENABLE = 1'b0;
        PWRITE = 1'b1;
        PADDR = 8'h08;
        PWDATA = control_data;
        ref_sample_valid = control_data[1];
        ref_qc_ok = control_data[2];
        ref_hour = intended_hour;
        ref_cams_pm25_x16 = intended_cams_x16;
        ref_pa_pm25_x16 = intended_pa_x16;
        @(negedge PCLK);
        PENABLE = 1'b1;
        ref_request_pulse = 1'b1;
        expected_dut_request = 1'b1;
        #1;
        check32("process_pready", 32'd1, {31'd0, PREADY});
        check32("process_pslverr", 32'd0, {31'd0, PSLVERR});
        @(posedge PCLK);
        transactions = transactions + 1;
        #1 capture_reference();
        @(negedge PCLK);
        ref_request_pulse = 1'b0;
        apb_idle();
    end
endtask

task apb_read;
    input [7:0] address;
    input [31:0] expected_data;
    input expected_error;
    begin
        @(negedge PCLK);
        PSEL = 1'b1;
        PENABLE = 1'b0;
        PWRITE = 1'b0;
        PADDR = address;
        PWDATA = 32'd0;
        @(negedge PCLK);
        PENABLE = 1'b1;
        #1;
        check32("read_pready", 32'd1, {31'd0, PREADY});
        check32("read_pslverr", {31'd0, expected_error},
                {31'd0, PSLVERR});
        check32("read_data", expected_data, PRDATA);
        @(posedge PCLK);
        transactions = transactions + 1;
        @(negedge PCLK);
        apb_idle();
    end
endtask

task apb_phase_gating_test;
    begin
        // A legal write must not take effect during SETUP.
        @(negedge PCLK);
        PSEL = 1'b1;
        PENABLE = 1'b0;
        PWRITE = 1'b1;
        PADDR = 8'h0C;
        PWDATA = 32'h1357_9BDF;
        #1 check32("setup_has_no_error", 32'd0, {31'd0, PSLVERR});
        @(posedge PCLK);
        #1 check32("setup_has_no_side_effect", 32'hFFFF_FF80,
                   dut.cams_pm25_x16_reg);
        @(negedge PCLK);
        PENABLE = 1'b1;
        #1 check32("access_write_error", 32'd0, {31'd0, PSLVERR});
        @(posedge PCLK);
        transactions = transactions + 1;
        #1 check32("access_write_side_effect", 32'h1357_9BDF,
                   dut.cams_pm25_x16_reg);
        @(negedge PCLK);
        apb_idle();
        #1 check32("idle_has_no_error", 32'd0, {31'd0, PSLVERR});
        apb_read(8'h0C, 32'h1357_9BDF, 1'b0);

        // An invalid address reports PSLVERR only in ACCESS.
        @(negedge PCLK);
        PSEL = 1'b1;
        PENABLE = 1'b0;
        PWRITE = 1'b0;
        PADDR = 8'h02;
        #1 check32("bad_setup_has_no_error", 32'd0, {31'd0, PSLVERR});
        @(negedge PCLK);
        PENABLE = 1'b1;
        #1 check32("bad_access_has_error", 32'd1, {31'd0, PSLVERR});
        @(posedge PCLK);
        transactions = transactions + 1;
        @(negedge PCLK);
        apb_idle();
        #1 check32("bad_idle_error_clears", 32'd0, {31'd0, PSLVERR});
    end
endtask

task wait_for_done;
    integer timeout;
    begin
        timeout = 0;
        while (!dut.done && timeout < 20) begin
            @(posedge PCLK);
            #1;
            timeout = timeout + 1;
        end
        check32("done_timeout", 32'd1, {31'd0, dut.done});
    end
endtask

task compare_internal_with_reference;
    reg [31:0] expected_status;
    begin
        #1;
        expected_status = {24'd0, captured_ref_alert_level,
                           captured_ref_alert_state, captured_ref_accepted,
                           captured_ref_result_valid, 1'b1, 1'b0};
        check32("native_equiv_status", expected_status,
                {24'd0, dut.status_alert_level, dut.status_alert_state,
                 dut.status_accepted, dut.status_result_valid,
                 dut.done, dut.busy});
        check32("native_equiv_result", captured_ref_fused_pm25_x16,
                dut.result_pm25_x16);
        check32("native_equiv_bias", captured_ref_bias_state_x16,
                dut.result_bias_state_x16);
    end
endtask

task compare_with_reference;
    reg [31:0] expected_status;
    begin
        #1;
        expected_status = {24'd0, captured_ref_alert_level,
                           captured_ref_alert_state, captured_ref_accepted,
                           captured_ref_result_valid, 1'b1, 1'b0};
        apb_read(8'h18, expected_status, 1'b0);
        apb_read(8'h1C, captured_ref_fused_pm25_x16, 1'b0);
        apb_read(8'h20, captured_ref_bias_state_x16, 1'b0);
    end
endtask

task run_transaction;
    input integer sample_valid;
    input integer qc_ok;
    input integer hour;
    input integer cams_x16;
    input integer pa_x16;
    begin
        apb_write(8'h0C, cams_x16, 1'b0);
        apb_write(8'h10, pa_x16, 1'b0);
        apb_write(8'h14, hour, 1'b0);
        apb_process({29'd0, qc_ok[0], sample_valid[0], 1'b1},
                    cams_x16, pa_x16, hour[4:0]);
        check32("busy_after_process", 32'd1, {31'd0, dut.busy});
        check32("done_cleared", 32'd0, {31'd0, dut.done});
        wait_for_done();
        compare_with_reference();
    end
endtask

// Starts a command and presents another PROCESS access while BUSY.  The
// second access must complete with PSLVERR and leave the first request intact.
task process_while_busy;
    integer ref_count_before_reject;
    integer dut_count_before_reject;
    begin
        @(negedge PCLK);
        PSEL = 1'b1;
        PENABLE = 1'b0;
        PWRITE = 1'b1;
        PADDR = 8'h08;
        PWDATA = 32'h00000007;
        ref_sample_valid = 1'b1;
        ref_qc_ok = 1'b1;
        ref_hour = 5'd9;
        ref_cams_pm25_x16 = 32'd320;
        ref_pa_pm25_x16 = 32'd400;
        @(negedge PCLK);
        PENABLE = 1'b1;
        ref_request_pulse = 1'b1;
        expected_dut_request = 1'b1;
        #1 check32("first_process_error", 32'd0, {31'd0, PSLVERR});
        @(posedge PCLK);
        transactions = transactions + 1;
        #1;
        capture_reference();
        check32("first_process_busy", 32'd1, {31'd0, dut.busy});

        @(negedge PCLK);
        ref_request_pulse = 1'b0;
        PENABLE = 1'b0;
        PWDATA = 32'h00000007;
        ref_count_before_reject = reference_requests;
        dut_count_before_reject = dut_core_requests;
        @(negedge PCLK);
        PENABLE = 1'b1;
        #1 check32("busy_process_error", 32'd1, {31'd0, PSLVERR});
        @(posedge PCLK);
        transactions = transactions + 1;
        @(negedge PCLK);
        apb_idle();
        wait_for_done();
        check32("busy_reject_no_reference_request", ref_count_before_reject,
                reference_requests);
        check32("busy_reject_one_dut_request", dut_count_before_reject + 1,
                dut_core_requests);
        compare_with_reference();
    end
endtask

// A legal payload write is allowed while BUSY but cannot alter the snapshot.
task atomic_snapshot_test;
    begin
        apb_write(8'h0C, 32'd100, 1'b0);
        apb_write(8'h10, 32'd180, 1'b0);
        apb_write(8'h14, 32'd12, 1'b0);

        @(negedge PCLK);
        PSEL = 1'b1;
        PENABLE = 1'b0;
        PWRITE = 1'b1;
        PADDR = 8'h08;
        PWDATA = 32'h00000007;
        ref_sample_valid = 1'b1;
        ref_qc_ok = 1'b1;
        ref_hour = 5'd12;
        ref_cams_pm25_x16 = 32'd100;
        ref_pa_pm25_x16 = 32'd180;
        @(negedge PCLK);
        PENABLE = 1'b1;
        ref_request_pulse = 1'b1;
        expected_dut_request = 1'b1;
        @(posedge PCLK);
        transactions = transactions + 1;
        #1 capture_reference();

        @(negedge PCLK);
        ref_request_pulse = 1'b0;
        PENABLE = 1'b0;
        PADDR = 8'h0C;
        PWDATA = 32'd2000;
        @(negedge PCLK);
        PENABLE = 1'b1;
        #1 check32("busy_payload_write_error", 32'd0, {31'd0, PSLVERR});
        @(posedge PCLK);
        transactions = transactions + 1;
        @(negedge PCLK);
        apb_idle();

        wait_for_done();
        compare_with_reference();
        check32("snapshot_fused_old_cams", 32'd100, dut.result_pm25_x16);
        apb_read(8'h0C, 32'd2000, 1'b0);
    end
endtask

// Prepare B's distinct CAMS value while A is in flight, then issue B in the
// first APB SETUP/ACCESS opportunity after DONE.  This checks that DONE clears
// and that neither payload nor result/status from A is reused for B.
task back_to_back_test;
    begin
        apb_write(8'h0C, 32'd160, 1'b0);
        apb_write(8'h10, 32'd400, 1'b0);
        apb_write(8'h14, 32'd21, 1'b0);
        apb_process(32'h00000007, 32'd160, 32'd400, 5'd21);

        // apb_process returns on the first negedge after acceptance, allowing
        // this next transfer to begin without an inserted idle cycle.
        PSEL = 1'b1;
        PENABLE = 1'b0;
        PWRITE = 1'b1;
        PADDR = 8'h0C;
        PWDATA = 32'd960;
        @(negedge PCLK);
        PENABLE = 1'b1;
        #1;
        check32("back_to_back_payload_error", 32'd0, {31'd0, PSLVERR});
        @(posedge PCLK);
        transactions = transactions + 1;
        @(negedge PCLK);
        apb_idle();

        wait_for_done();
        compare_internal_with_reference();
        check32("transaction_a_result", 32'd160, dut.result_pm25_x16);

        apb_process(32'h00000007, 32'd960, 32'd400, 5'd21);
        check32("transaction_b_busy", 32'd1, {31'd0, dut.busy});
        check32("transaction_b_done_cleared", 32'd0, {31'd0, dut.done});
        wait_for_done();
        compare_with_reference();
        check32("transaction_b_not_stale", 32'd990, dut.result_pm25_x16);
    end
endtask

task apply_reset;
    begin
        PRESETn = 1'b0;
        apb_idle();
        repeat (3) @(posedge PCLK);
        PRESETn = 1'b1;
        repeat (2) @(posedge PCLK);
        #1;
    end
endtask

initial begin
    PRESETn = 1'b0;
    errors = 0;
    transactions = 0;
    checks = 0;
    reference_requests = 0;
    dut_core_requests = 0;
    ref_request_pulse = 1'b0;
    ref_sample_valid = 1'b0;
    ref_qc_ok = 1'b0;
    ref_hour = 5'd0;
    ref_cams_pm25_x16 = 32'sd0;
    ref_pa_pm25_x16 = 32'sd0;
    expected_dut_request = 1'b0;
    captured_ref_result_valid = 1'b0;
    captured_ref_accepted = 1'b0;
    captured_ref_alert_level = 3'd0;
    captured_ref_alert_state = 1'b0;
    captured_ref_fused_pm25_x16 = 32'sd0;
    captured_ref_bias_state_x16 = 32'sd0;
    apb_idle();

    apply_reset();

    // Reset values, identity/configuration constants, and reserved bits.
    apb_read(8'h00, 32'h504D3235, 1'b0);
    apb_read(8'h04, 32'h00010000, 1'b0);
    apb_read(8'h08, 32'd0, 1'b0);
    apb_read(8'h18, 32'd0, 1'b0);
    apb_read(8'h1C, 32'd0, 1'b0);
    apb_read(8'h20, 32'd0, 1'b0);
    apb_read(8'h24, 32'h00001003, 1'b0);

    // Legal write/readback; upper HOUR and CONTROL bits read as zero.
    apb_write(8'h0C, 32'hFFFF_FF80, 1'b0);
    apb_write(8'h10, 32'h0000_1234, 1'b0);
    apb_write(8'h14, 32'hFFFF_FFE7, 1'b0);
    apb_write(8'h08, 32'hFFFF_FFFE, 1'b0);
    apb_read(8'h0C, 32'hFFFF_FF80, 1'b0);
    apb_read(8'h10, 32'h0000_1234, 1'b0);
    apb_read(8'h14, 32'd7, 1'b0);
    apb_read(8'h08, 32'd6, 1'b0);
    apb_phase_gating_test();

    // Read-only, misaligned, and unmapped protection.
    apb_write(8'h00, 32'd0, 1'b1);
    apb_write(8'h18, 32'd0, 1'b1);
    apb_read(8'h02, 32'd0, 1'b1);
    apb_write(8'h0D, 32'd1, 1'b1);
    apb_read(8'h28, 32'd0, 1'b1);
    apb_write(8'h28, 32'd1, 1'b1);

    apply_reset();

    // Positive adaptation, corrected output, and alert classification.
    run_transaction(1, 1, 5, 448, 512);
    check32("positive_bias", 32'd8, dut.result_bias_state_x16);
    check32("pre_update_fused", 32'd448, dut.result_pm25_x16);
    check32("accepted_good", 32'd1, {31'd0, dut.status_accepted});

    // QC fail holds bias while a valid sample can change hysteresis.
    run_transaction(1, 0, 6, 600, 0);
    check32("qc_fail_bias_hold", 32'd8, dut.result_bias_state_x16);
    check32("qc_fail_accepted", 32'd0, {31'd0, dut.status_accepted});
    check32("alert_on", 32'd1, {31'd0, dut.status_alert_state});
    check32("alert_level", 32'd2, {29'd0, dut.status_alert_level});

    // A PROCESS command with SAMPLE_VALID=0 still completes and holds state.
    run_transaction(0, 1, 7, -160, -320);
    check32("invalid_result_valid", 32'd0,
            {31'd0, dut.status_result_valid});
    check32("invalid_bias_hold", 32'd8, dut.result_bias_state_x16);
    check32("invalid_hysteresis_hold", 32'd1,
            {31'd0, dut.status_alert_state});

    // Signed negative residual and arithmetic shift update bias from 8 to -1.
    run_transaction(1, 1, 8, -32, -96);
    check32("negative_bias", 32'hFFFF_FFFF, dut.result_bias_state_x16);
    check32("negative_fused_saturates", 32'd0, dut.result_pm25_x16);
    check32("alert_off", 32'd0, {31'd0, dut.status_alert_state});

    // Busy rejection and consecutive accepted transactions.
    apb_write(8'h0C, 32'd320, 1'b0);
    apb_write(8'h10, 32'd400, 1'b0);
    apb_write(8'h14, 32'd9, 1'b0);
    process_while_busy();
    run_transaction(1, 0, 10, 640, 0);

    // Writes after PROCESS do not alter an in-flight snapshot.
    apply_reset();
    atomic_snapshot_test();

    // Back-to-back accepted commands use fresh payload and status.
    apply_reset();
    back_to_back_test();

    // Reset after state exists restores all software-visible mutable state.
    apply_reset();
    apb_read(8'h08, 32'd0, 1'b0);
    apb_read(8'h18, 32'd0, 1'b0);
    apb_read(8'h1C, 32'd0, 1'b0);
    apb_read(8'h20, 32'd0, 1'b0);

    if (errors == 0) begin
        $display("[pm25-apb] protocol-and-native-equivalence: PASS");
        $display("[pm25-apb] summary: PASS transactions=%0d checks=%0d",
                 transactions, checks);
        $finish;
    end else begin
        $display("[pm25-apb] summary: FAIL transactions=%0d checks=%0d errors=%0d",
                 transactions, checks, errors);
        $fatal(1);
    end
end

endmodule
