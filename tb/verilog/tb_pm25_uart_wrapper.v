`timescale 1ns/1ps

// Packet-level end-to-end regression for request scheduling, core state, and
// response encoding. UART RX/TX bit timing is bypassed; the real 8N1 path is
// covered separately by tb_pm25_uart_serial_top.
module tb_pm25_uart_wrapper;

reg clk;
reg rst_n;
reg serial_rx;
wire serial_tx;

reg request_valid;
reg request_checksum_error;
reg request_sample_valid;
reg request_qc_ok;
reg [4:0] request_hour;
reg signed [31:0] request_cams_x16;
reg signed [31:0] request_pa_x16;

reg emulated_tx_busy;
integer busy_count;
reg [7:0] captured [0:127];
integer captured_count;
integer errors;
integer printed_mismatches;

pm25_uart_demo_top #(
    .CLK_FREQ_HZ(1000000),
    .BAUD_RATE(100000),
    .ALPHA_SHIFT(3)
) dut (
    .clk(clk),
    .rst_n(rst_n),
    .uart_rx(serial_rx),
    .uart_tx(serial_tx)
);

initial clk = 1'b0;
always #5 clk = ~clk;

// Drive the packet-decoder boundary directly so this test remains fast while
// still exercising the wrapper scheduler, core, and packet transmitter.
initial begin
    force dut.packet_valid = request_valid;
    force dut.checksum_error = request_checksum_error;
    force dut.sample_valid_to_core = request_sample_valid;
    force dut.qc_ok_to_core = request_qc_ok;
    force dut.hour_to_core = request_hour;
    force dut.cams_pm25_x16_to_core = request_cams_x16;
    force dut.pa_pm25_x16_to_core = request_pa_x16;
    force dut.uart_tx_busy = emulated_tx_busy;
end

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        emulated_tx_busy <= 1'b0;
        busy_count <= 0;
        captured_count <= 0;
    end else begin
        if (dut.uart_tx_start) begin
            captured[captured_count] <= dut.uart_tx_data;
            captured_count <= captured_count + 1;
            emulated_tx_busy <= 1'b1;
            busy_count <= 2;
        end else if (busy_count > 0) begin
            busy_count <= busy_count - 1;
            if (busy_count == 1) begin
                emulated_tx_busy <= 1'b0;
            end
        end
    end
end

function [7:0] output_checksum;
    input [7:0] b0;
    input [7:0] b1;
    input [7:0] b2;
    input [7:0] b3;
    input [7:0] b4;
    input [7:0] b5;
    input [7:0] b6;
    input [7:0] b7;
    input [7:0] b8;
    begin
        output_checksum = b0 + b1 + b2 + b3 + b4 + b5 + b6 + b7 + b8;
    end
endfunction

task mismatch;
    input [255:0] field_name;
    input integer expected_value;
    input integer actual_value;
    begin
        errors = errors + 1;
        if (printed_mismatches < 30) begin
            $display(
                "MISMATCH wrapper field=%0s exp=%0d got=%0d",
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
            mismatch(field_name, expected_value, actual_value);
        end
    end
endtask

task send_request;
    input integer sample_valid;
    input integer qc_ok;
    input integer hour;
    input integer cams_x16;
    input integer pa_x16;
    begin
        while (dut.tx_active || dut.response_pending || emulated_tx_busy) begin
            @(posedge clk);
        end
        @(negedge clk);
        request_sample_valid = sample_valid[0];
        request_qc_ok = qc_ok[0];
        request_hour = hour[4:0];
        request_cams_x16 = cams_x16;
        request_pa_x16 = pa_x16;
        request_valid = 1'b1;
        @(posedge clk);
        #1;
        request_valid = 1'b0;
    end
endtask

task wait_for_packet;
    input integer expected_total;
    integer timeout;
    begin
        timeout = 0;
        while ((captured_count < expected_total) && (timeout < 3000)) begin
            @(posedge clk);
            timeout = timeout + 1;
        end
        if (captured_count != expected_total) begin
            mismatch("response_byte_count", expected_total, captured_count);
        end
    end
endtask

task check_packet;
    input integer base;
    input integer result_valid;
    input integer accepted;
    input integer alert_level;
    input integer alert_state;
    input integer fused_x16;
    input integer bias_x16;
    reg [15:0] fused_bits;
    reg [15:0] bias_bits;
    reg [7:0] checksum;
    begin
        fused_bits = fused_x16[15:0];
        bias_bits = bias_x16[15:0];
        checksum = output_checksum(
            8'h5A,
            result_valid[7:0],
            accepted[7:0],
            alert_level[7:0],
            alert_state[7:0],
            fused_bits[15:8],
            fused_bits[7:0],
            bias_bits[15:8],
            bias_bits[7:0]
        );
        check_value("start", 8'h5A, captured[base + 0]);
        check_value("result_valid", result_valid, captured[base + 1]);
        check_value("accepted", accepted, captured[base + 2]);
        check_value("alert_level", alert_level, captured[base + 3]);
        check_value("alert_state", alert_state, captured[base + 4]);
        check_value("fused_hi", fused_bits[15:8], captured[base + 5]);
        check_value("fused_lo", fused_bits[7:0], captured[base + 6]);
        check_value("bias_hi", bias_bits[15:8], captured[base + 7]);
        check_value("bias_lo", bias_bits[7:0], captured[base + 8]);
        check_value("checksum", checksum, captured[base + 9]);
    end
endtask

task pulse_bad_checksum;
    integer before_count;
    begin
        before_count = captured_count;
        @(negedge clk);
        request_checksum_error = 1'b1;
        request_valid = 1'b0;
        @(posedge clk);
        #1;
        request_checksum_error = 1'b0;
        repeat (100) @(posedge clk);
        check_value("bad_checksum_no_response", before_count, captured_count);
    end
endtask

task apply_reset;
    begin
        rst_n = 1'b0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (3) @(posedge clk);
    end
endtask

initial begin
    rst_n = 1'b0;
    serial_rx = 1'b1;
    request_valid = 1'b0;
    request_checksum_error = 1'b0;
    request_sample_valid = 1'b0;
    request_qc_ok = 1'b0;
    request_hour = 5'd0;
    request_cams_x16 = 32'sd0;
    request_pa_x16 = 32'sd0;
    emulated_tx_busy = 1'b0;
    busy_count = 0;
    captured_count = 0;
    errors = 0;
    printed_mismatches = 0;

    apply_reset();

    // Valid + QC good: update bias from 0 to 8.
    send_request(1, 1, 5, 448, 512);
    wait_for_packet(10);
    check_packet(0, 1, 1, 1, 0, 448, 8);

    // Stop-and-wait second good packet: valid result, QC holds bias.
    send_request(1, 0, 6, 600, 0);
    wait_for_packet(20);
    check_packet(10, 1, 0, 2, 1, 608, 8);

    // Invalid packets still receive one golden-model response. Bias and
    // hysteresis must hold even when their numeric inputs would change state.
    send_request(0, 0, 7, 1000, 2000);
    wait_for_packet(30);
    check_packet(20, 0, 0, 3, 1, 1008, 8);
    check_value("invalid_qc0_bias_hold", 8, dut.core_bias_state_x16);
    check_value("invalid_qc0_hysteresis_hold", 1, dut.core_alert_state_after);

    send_request(0, 1, 8, -160, -320);
    wait_for_packet(40);
    check_packet(30, 0, 0, 0, 1, 0, 8);
    check_value("invalid_qc1_bias_hold", 8, dut.core_bias_state_x16);
    check_value("invalid_qc1_hysteresis_hold", 1, dut.core_alert_state_after);

    // Signed negative values and arithmetic shift on a valid transaction.
    send_request(1, 1, 9, -32, -96);
    wait_for_packet(50);
    check_packet(40, 1, 1, 0, 0, 0, -1);

    // A checksum error is observable but cannot create a core request/response.
    pulse_bad_checksum();
    check_value("bad_checksum_bias_hold", -1, dut.core_bias_state_x16);
    check_value("bad_checksum_hysteresis_hold", 0, dut.core_alert_state_after);

    // Reset between sequences restores persistent state deterministically.
    apply_reset();
    check_value("reset_bias", 0, dut.core_bias_state_x16);
    check_value("reset_hysteresis", 0, dut.core_alert_state_after);
    send_request(1, 1, 5, 448, 512);
    wait_for_packet(10);
    check_packet(0, 1, 1, 1, 0, 448, 8);

    if (errors == 0) begin
        $display("[pm25-uart-wrapper] request-contract: PASS");
        $display("[pm25-uart-wrapper] summary: PASS");
        $finish;
    end else begin
        $display("[pm25-uart-wrapper] summary: FAIL errors=%0d", errors);
        $fatal(1);
    end
end

endmodule
