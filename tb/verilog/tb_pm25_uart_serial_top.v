`timescale 1ns/1ps

// End-to-end 8N1 serial regression for the generic UART top.
module tb_pm25_uart_serial_top;

localparam integer CLK_FREQ_HZ = 1000000;
localparam integer BAUD_RATE = 100000;
localparam integer CLKS_PER_BIT = CLK_FREQ_HZ / BAUD_RATE;

reg clk;
reg rst_n;
reg serial_rx;
wire serial_tx;
wire monitor_valid;
wire [7:0] monitor_byte;
reg [7:0] captured [0:127];
integer captured_count;
integer errors;
integer index;

pm25_uart_demo_top #(
    .CLK_FREQ_HZ(CLK_FREQ_HZ),
    .BAUD_RATE(BAUD_RATE),
    .ALPHA_SHIFT(3)
) dut (
    .clk(clk),
    .rst_n(rst_n),
    .uart_rx(serial_rx),
    .uart_tx(serial_tx)
);

uart_rx #(
    .CLK_FREQ_HZ(CLK_FREQ_HZ),
    .BAUD_RATE(BAUD_RATE)
) monitor (
    .clk(clk),
    .rst_n(rst_n),
    .rx(serial_tx),
    .data_valid(monitor_valid),
    .data_byte(monitor_byte)
);

initial clk = 1'b0;
always #5 clk = ~clk;

always @(posedge clk) begin
    if (!rst_n) begin
        captured_count <= 0;
    end else if (monitor_valid) begin
        captured[captured_count] <= monitor_byte;
        captured_count <= captured_count + 1;
    end
end

function [7:0] input_checksum;
    input [7:0] b0;
    input [7:0] b1;
    input [7:0] b2;
    input [7:0] b3;
    input [7:0] b4;
    input [7:0] b5;
    input [7:0] b6;
    input [7:0] b7;
    begin
        input_checksum = b0 + b1 + b2 + b3 + b4 + b5 + b6 + b7;
    end
endfunction

task send_uart_byte;
    input [7:0] value;
    integer bit_number;
    begin
        serial_rx = 1'b0;
        repeat (CLKS_PER_BIT) @(posedge clk);
        for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
            serial_rx = value[bit_number];
            repeat (CLKS_PER_BIT) @(posedge clk);
        end
        serial_rx = 1'b1;
        repeat (CLKS_PER_BIT) @(posedge clk);
    end
endtask

task send_bad_checksum_packet;
    input [7:0] valid;
    input [7:0] qc;
    input [7:0] hour;
    input [15:0] cams;
    input [15:0] pa;
    reg [7:0] sum;
    begin
        sum = input_checksum(
            8'hA5,
            valid,
            qc,
            hour,
            cams[15:8],
            cams[7:0],
            pa[15:8],
            pa[7:0]
        );
        send_uart_byte(8'hA5);
        send_uart_byte(valid);
        send_uart_byte(qc);
        send_uart_byte(hour);
        send_uart_byte(cams[15:8]);
        send_uart_byte(cams[7:0]);
        send_uart_byte(pa[15:8]);
        send_uart_byte(pa[7:0]);
        send_uart_byte(sum + 8'd1);
    end
endtask

task send_packet;
    input [7:0] valid;
    input [7:0] qc;
    input [7:0] hour;
    input [15:0] cams;
    input [15:0] pa;
    reg [7:0] sum;
    begin
        sum = input_checksum(
            8'hA5,
            valid,
            qc,
            hour,
            cams[15:8],
            cams[7:0],
            pa[15:8],
            pa[7:0]
        );
        send_uart_byte(8'hA5);
        send_uart_byte(valid);
        send_uart_byte(qc);
        send_uart_byte(hour);
        send_uart_byte(cams[15:8]);
        send_uart_byte(cams[7:0]);
        send_uart_byte(pa[15:8]);
        send_uart_byte(pa[7:0]);
        send_uart_byte(sum);
    end
endtask

task wait_for_responses;
    input integer expected_count;
    integer timeout;
    begin
        timeout = 0;
        while ((captured_count < expected_count) && (timeout < 20000)) begin
            @(posedge clk);
            timeout = timeout + 1;
        end
        if (captured_count != expected_count) begin
            $display(
                "MISMATCH serial response count exp=%0d got=%0d",
                expected_count,
                captured_count
            );
            errors = errors + 1;
        end
    end
endtask

task check_byte;
    input integer position;
    input [7:0] expected;
    begin
        if (captured[position] !== expected) begin
            $display(
                "MISMATCH serial byte=%0d exp=0x%02x got=0x%02x",
                position,
                expected,
                captured[position]
            );
            errors = errors + 1;
        end
    end
endtask

task check_value;
    input [255:0] field_name;
    input integer expected;
    input integer actual;
    begin
        if (actual !== expected) begin
            $display(
                "MISMATCH serial field=%0s exp=%0d got=%0d",
                field_name,
                expected,
                actual
            );
            errors = errors + 1;
        end
    end
endtask

task assert_no_response;
    input integer expected_count;
    begin
        repeat (3000) @(posedge clk);
        check_value("bad_checksum_no_response", expected_count, captured_count);
    end
endtask

task apply_reset;
    begin
        rst_n = 1'b0;
        serial_rx = 1'b1;
        repeat (8) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);
    end
endtask

initial begin
    rst_n = 1'b0;
    serial_rx = 1'b1;
    captured_count = 0;
    errors = 0;
    repeat (8) @(posedge clk);
    rst_n = 1'b1;
    repeat (4) @(posedge clk);

    // First request is accepted: residual=64, delta=8, fused uses pre-update bias=0.
    send_packet(8'd1, 8'd1, 8'd5, 16'd448, 16'd512);
    wait_for_responses(10);
    check_byte(0, 8'h5A);
    check_byte(1, 8'd1);
    check_byte(2, 8'd1);
    check_byte(3, 8'd1);
    check_byte(4, 8'd0);
    check_byte(5, 8'h01);
    check_byte(6, 8'hC0);
    check_byte(7, 8'h00);
    check_byte(8, 8'h08);
    check_byte(9, 8'h26);

    // Stop-and-wait next request: qc fail holds bias=8; fused=600+8; alert turns on.
    send_packet(8'd1, 8'd0, 8'd6, 16'd600, 16'd0);
    wait_for_responses(20);
    check_byte(10, 8'h5A);
    check_byte(11, 8'd1);
    check_byte(12, 8'd0);
    check_byte(13, 8'd2);
    check_byte(14, 8'd1);
    check_byte(15, 8'h02);
    check_byte(16, 8'h60);
    check_byte(17, 8'h00);
    check_byte(18, 8'h08);
    check_byte(19, 8'hC8);

    // Invalid + QC low: one response, no bias/hysteresis update.
    send_packet(8'd0, 8'd0, 8'd7, 16'd1000, 16'd2000);
    wait_for_responses(30);
    check_byte(20, 8'h5A);
    check_byte(21, 8'd0);
    check_byte(22, 8'd0);
    check_byte(23, 8'd3);
    check_byte(24, 8'd1);
    check_byte(25, 8'h03);
    check_byte(26, 8'hF0);
    check_byte(27, 8'h00);
    check_byte(28, 8'h08);
    check_byte(29, 8'h59);
    check_value("invalid_qc0_bias_hold", 8, dut.core_bias_state_x16);
    check_value("invalid_qc0_hysteresis_hold", 1, dut.core_alert_state_after);

    // Invalid + QC high must still hold both persistent states. Signed inputs
    // make the frozen diagnostic fused result saturate to zero.
    send_packet(8'd0, 8'd1, 8'd8, 16'hFF60, 16'hFEC0);
    wait_for_responses(40);
    check_byte(30, 8'h5A);
    check_byte(31, 8'd0);
    check_byte(32, 8'd0);
    check_byte(33, 8'd0);
    check_byte(34, 8'd1);
    check_byte(35, 8'h00);
    check_byte(36, 8'h00);
    check_byte(37, 8'h00);
    check_byte(38, 8'h08);
    check_byte(39, 8'h63);
    check_value("invalid_qc1_bias_hold", 8, dut.core_bias_state_x16);
    check_value("invalid_qc1_hysteresis_hold", 1, dut.core_alert_state_after);

    // Signed negative valid transaction: arithmetic shift updates bias to -1.
    send_packet(8'd1, 8'd1, 8'd9, 16'hFFE0, 16'hFFA0);
    wait_for_responses(50);
    check_byte(40, 8'h5A);
    check_byte(41, 8'd1);
    check_byte(42, 8'd1);
    check_byte(43, 8'd0);
    check_byte(44, 8'd0);
    check_byte(45, 8'h00);
    check_byte(46, 8'h00);
    check_byte(47, 8'hFF);
    check_byte(48, 8'hFF);
    check_byte(49, 8'h5A);

    // Bad checksum: no response/state update; next checksum-valid packet still
    // receives exactly one response with the preserved bias.
    send_bad_checksum_packet(8'd1, 8'd1, 8'd10, 16'd1000, 16'd2000);
    assert_no_response(50);
    check_value("bad_checksum_bias_hold", -1, dut.core_bias_state_x16);
    check_value("bad_checksum_hysteresis_hold", 0, dut.core_alert_state_after);
    send_packet(8'd1, 8'd0, 8'd11, 16'd0, 16'd0);
    wait_for_responses(60);
    check_byte(50, 8'h5A);
    check_byte(51, 8'd1);
    check_byte(52, 8'd0);
    check_byte(53, 8'd0);
    check_byte(54, 8'd0);
    check_byte(55, 8'h00);
    check_byte(56, 8'h00);
    check_byte(57, 8'hFF);
    check_byte(58, 8'hFF);
    check_byte(59, 8'h59);

    // Reset between sequences restores deterministic state and response count.
    apply_reset();
    check_value("reset_bias", 0, dut.core_bias_state_x16);
    check_value("reset_hysteresis", 0, dut.core_alert_state_after);
    send_packet(8'd1, 8'd1, 8'd5, 16'd448, 16'd512);
    wait_for_responses(10);
    check_byte(0, 8'h5A);
    check_byte(1, 8'd1);
    check_byte(2, 8'd1);
    check_byte(3, 8'd1);
    check_byte(4, 8'd0);
    check_byte(5, 8'h01);
    check_byte(6, 8'hC0);
    check_byte(7, 8'h00);
    check_byte(8, 8'h08);
    check_byte(9, 8'h26);

    if (errors == 0) begin
        $display("[pm25-uart-serial] request-contract-and-reset: PASS");
        $display("[pm25-uart-serial] summary: PASS");
        $finish;
    end else begin
        $display("[pm25-uart-serial] summary: FAIL errors=%0d", errors);
        $fatal(1);
    end
end

endmodule
