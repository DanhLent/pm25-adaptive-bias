`timescale 1ns/1ps

// Self-checking CSV-vector testbench for pm25_alert_core.
module tb_pm25_alert_core;

parameter integer ALPHA_SHIFT = 3;

reg clk;
reg rst_n;
reg sample_valid;
reg qc_ok;
reg [4:0] hour;
reg signed [31:0] cams_pm25_x16;
reg signed [31:0] pa_pm25_x16;

wire sample_ready;
wire result_valid;
wire accepted;
wire [4:0] hour_out;
wire signed [31:0] bias_before_x16;
wire signed [31:0] residual_x16;
wire signed [31:0] error_x16;
wire signed [31:0] delta_x16;
wire signed [31:0] bias_after_x16;
wire signed [31:0] fused_raw_x16;
wire signed [31:0] fused_pm25_x16;
wire [2:0] alert_level;
wire alert_state_before;
wire alert_state_after;
wire signed [31:0] bias_state_x16;

reg verbose;
reg [1023:0] vector_path;
reg [1023:0] vector_name;
reg [4095:0] csv_line;
integer vector_fd;
integer line_ok;
integer scan_count;
integer total_samples;
integer total_errors;
integer printed_mismatches;

integer sample_index_i;
integer sample_valid_i;
integer qc_ok_i;
integer hour_i;
integer cams_pm25_x16_i;
integer pa_pm25_x16_i;
integer exp_result_valid_i;
integer exp_accepted_i;
integer exp_bias_before_x16_i;
integer exp_residual_x16_i;
integer exp_error_x16_i;
integer exp_delta_x16_i;
integer exp_bias_after_x16_i;
integer exp_fused_raw_x16_i;
integer exp_fused_pm25_x16_i;
integer exp_alert_level_i;
integer exp_alert_state_before_i;
integer exp_alert_state_after_i;

pm25_alert_core #(
    .ALPHA_SHIFT(ALPHA_SHIFT)
) dut (
    .clk(clk),
    .rst_n(rst_n),
    .sample_valid(sample_valid),
    .qc_ok(qc_ok),
    .hour(hour),
    .cams_pm25_x16(cams_pm25_x16),
    .pa_pm25_x16(pa_pm25_x16),
    .sample_ready(sample_ready),
    .result_valid(result_valid),
    .accepted(accepted),
    .hour_out(hour_out),
    .bias_before_x16(bias_before_x16),
    .residual_x16(residual_x16),
    .error_x16(error_x16),
    .delta_x16(delta_x16),
    .bias_after_x16(bias_after_x16),
    .fused_raw_x16(fused_raw_x16),
    .fused_pm25_x16(fused_pm25_x16),
    .alert_level(alert_level),
    .alert_state_before(alert_state_before),
    .alert_state_after(alert_state_after),
    .bias_state_x16(bias_state_x16)
);

initial begin
    clk = 1'b0;
end

always #5 clk = ~clk;

task print_mismatch;
    input integer sample_number;
    input [255:0] field_name;
    input integer expected_value;
    input integer actual_value;
    begin
        if (printed_mismatches < 20) begin
            $display(
                "MISMATCH sample=%0d field=%0s exp=%0d got=%0d",
                sample_number,
                field_name,
                expected_value,
                actual_value
            );
            printed_mismatches = printed_mismatches + 1;
        end
    end
endtask

task check_value;
    input [255:0] field_name;
    input integer expected_value;
    input integer actual_value;
    begin
        if (actual_value !== expected_value) begin
            total_errors = total_errors + 1;
            print_mismatch(sample_index_i, field_name, expected_value, actual_value);
        end
    end
endtask

task check_reset_zero;
    begin
        check_value("reset.sample_ready", 1, sample_ready);
        check_value("reset.result_valid", 0, result_valid);
        check_value("reset.accepted", 0, accepted);
        check_value("reset.hour_out", 0, hour_out);
        check_value("reset.bias_before_x16", 0, bias_before_x16);
        check_value("reset.residual_x16", 0, residual_x16);
        check_value("reset.error_x16", 0, error_x16);
        check_value("reset.delta_x16", 0, delta_x16);
        check_value("reset.bias_after_x16", 0, bias_after_x16);
        check_value("reset.fused_raw_x16", 0, fused_raw_x16);
        check_value("reset.fused_pm25_x16", 0, fused_pm25_x16);
        check_value("reset.alert_level", 0, alert_level);
        check_value("reset.alert_state_before", 0, alert_state_before);
        check_value("reset.alert_state_after", 0, alert_state_after);
        check_value("reset.bias_state_x16", 0, bias_state_x16);
    end
endtask

task apply_and_check_sample;
    begin
        if (sample_index_i != total_samples) begin
            total_errors = total_errors + 1;
            print_mismatch(sample_index_i, "sample_index_sequence", total_samples, sample_index_i);
        end

        sample_valid = sample_valid_i[0];
        qc_ok = qc_ok_i[0];
        hour = hour_i[4:0];
        cams_pm25_x16 = cams_pm25_x16_i;
        pa_pm25_x16 = pa_pm25_x16_i;

        @(posedge clk);
        #1;

        check_value("sample_ready", 1, sample_ready);
        check_value("result_valid", exp_result_valid_i, result_valid);
        check_value("accepted", exp_accepted_i, accepted);
        check_value("hour_out", hour_i, hour_out);
        check_value("bias_before_x16", exp_bias_before_x16_i, bias_before_x16);
        check_value("residual_x16", exp_residual_x16_i, residual_x16);
        check_value("error_x16", exp_error_x16_i, error_x16);
        check_value("delta_x16", exp_delta_x16_i, delta_x16);
        check_value("bias_after_x16", exp_bias_after_x16_i, bias_after_x16);
        check_value("fused_raw_x16", exp_fused_raw_x16_i, fused_raw_x16);
        check_value("fused_pm25_x16", exp_fused_pm25_x16_i, fused_pm25_x16);
        check_value("alert_level", exp_alert_level_i, alert_level);
        check_value("alert_state_before", exp_alert_state_before_i, alert_state_before);
        check_value("alert_state_after", exp_alert_state_after_i, alert_state_after);
        check_value("bias_state_x16", exp_bias_after_x16_i, bias_state_x16);

        if (verbose) begin
            $display(
                "TB_SAMPLE vector=%0s sample=%0d valid=%0d accepted=%0d fused=%0d alert=%0d",
                vector_name,
                sample_index_i,
                result_valid,
                accepted,
                fused_pm25_x16,
                alert_level
            );
        end

        total_samples = total_samples + 1;
        @(negedge clk);
    end
endtask

initial begin
    vector_path = "data/test_vectors/core_v1_zero_residual.csv";
    vector_name = "core_v1_zero_residual";
    verbose = $test$plusargs("VERBOSE");
    if ($value$plusargs("VECTOR=%s", vector_path)) begin
        vector_name = vector_path;
    end
    if ($value$plusargs("VECTOR_NAME=%s", vector_name)) begin
        vector_name = vector_name;
    end

    total_samples = 0;
    total_errors = 0;
    printed_mismatches = 0;
    sample_index_i = 0;
    sample_valid = 1'b0;
    qc_ok = 1'b0;
    hour = 5'd0;
    cams_pm25_x16 = 32'sd0;
    pa_pm25_x16 = 32'sd0;
    rst_n = 1'b0;

    if (verbose) begin
        $display("TB_INFO vector=%0s path=%0s", vector_name, vector_path);
    end

    repeat (2) @(posedge clk);
    #1;
    check_reset_zero();
    @(negedge clk);
    rst_n = 1'b1;

    vector_fd = $fopen(vector_path, "r");
    if (vector_fd == 0) begin
        $display("TB_FATAL open_failed vector=%0s", vector_path);
        $fatal(1);
    end

    line_ok = $fgets(csv_line, vector_fd);
    if (line_ok == 0) begin
        $display("TB_FATAL empty_vector vector=%0s", vector_path);
        $fatal(1);
    end

    @(negedge clk);
    line_ok = $fgets(csv_line, vector_fd);
    while (line_ok != 0) begin
        scan_count = $sscanf(
            csv_line,
            "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d",
            sample_index_i,
            sample_valid_i,
            qc_ok_i,
            hour_i,
            cams_pm25_x16_i,
            pa_pm25_x16_i,
            exp_result_valid_i,
            exp_accepted_i,
            exp_bias_before_x16_i,
            exp_residual_x16_i,
            exp_error_x16_i,
            exp_delta_x16_i,
            exp_bias_after_x16_i,
            exp_fused_raw_x16_i,
            exp_fused_pm25_x16_i,
            exp_alert_level_i,
            exp_alert_state_before_i,
            exp_alert_state_after_i
        );

        if (scan_count == 18) begin
            apply_and_check_sample();
        end else if (scan_count != 0) begin
            total_errors = total_errors + 1;
            print_mismatch(total_samples, "csv_field_count", 18, scan_count);
        end

        line_ok = $fgets(csv_line, vector_fd);
    end

    $fclose(vector_fd);

    // Verify asynchronous reset after a stateful sequence, not only at startup.
    @(negedge clk);
    rst_n = 1'b0;
    #1;
    check_reset_zero();

    if (total_errors == 0) begin
        $display("TB_RESULT PASS vector=%0s samples=%0d errors=0", vector_name, total_samples);
        $finish;
    end else begin
        $display(
            "TB_RESULT FAIL vector=%0s samples=%0d errors=%0d",
            vector_name,
            total_samples,
            total_errors
        );
        $fatal(1);
    end
end

endmodule
