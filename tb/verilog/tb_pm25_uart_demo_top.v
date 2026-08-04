`timescale 1ns/1ps

// Packet-level tests for the PM2.5 UART demo wrapper components.
module tb_pm25_uart_demo_top;

reg clk;
reg rst_n;

reg rx_valid;
reg [7:0] rx_byte;
wire rx_sample_valid;
wire rx_qc_ok;
wire [4:0] rx_hour;
wire signed [31:0] rx_cams_pm25_x16;
wire signed [31:0] rx_pa_pm25_x16;
wire rx_packet_valid;
wire rx_checksum_error;

reg tx_start_packet;
reg tx_result_valid;
reg tx_accepted;
reg [2:0] tx_alert_level;
reg tx_alert_state;
reg signed [31:0] tx_fused_pm25_x16;
reg signed [31:0] tx_bias_state_x16;
reg tx_uart_busy;
wire tx_uart_start;
wire [7:0] tx_uart_data;
wire tx_packet_done;

reg [7:0] captured_tx [0:15];
integer captured_count;
integer busy_count;
integer rx_errors;
integer tx_errors;
integer printed_mismatches;

pm25_packet_rx u_packet_rx (
    .clk(clk),
    .rst_n(rst_n),
    .rx_valid(rx_valid),
    .rx_byte(rx_byte),
    .sample_valid_out(rx_sample_valid),
    .qc_ok_out(rx_qc_ok),
    .hour_out(rx_hour),
    .cams_pm25_x16_out(rx_cams_pm25_x16),
    .pa_pm25_x16_out(rx_pa_pm25_x16),
    .packet_valid(rx_packet_valid),
    .checksum_error(rx_checksum_error)
);

pm25_packet_tx u_packet_tx (
    .clk(clk),
    .rst_n(rst_n),
    .start(tx_start_packet),
    .result_valid(tx_result_valid),
    .accepted(tx_accepted),
    .alert_level(tx_alert_level),
    .alert_state(tx_alert_state),
    .fused_pm25_x16(tx_fused_pm25_x16),
    .bias_state_x16(tx_bias_state_x16),
    .tx_busy(tx_uart_busy),
    .tx_start(tx_uart_start),
    .tx_data(tx_uart_data),
    .done(tx_packet_done)
);

initial begin
    clk = 1'b0;
end

always #5 clk = ~clk;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        tx_uart_busy <= 1'b0;
        busy_count <= 0;
        captured_count <= 0;
    end else begin
        if (tx_uart_start) begin
            captured_tx[captured_count] <= tx_uart_data;
            captured_count <= captured_count + 1;
            tx_uart_busy <= 1'b1;
            busy_count <= 2;
        end else if (busy_count > 0) begin
            busy_count <= busy_count - 1;
            if (busy_count == 1) begin
                tx_uart_busy <= 1'b0;
            end
        end
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

task print_mismatch;
    input [255:0] section;
    input [255:0] field_name;
    input integer expected_value;
    input integer actual_value;
    begin
        if (printed_mismatches < 20) begin
            $display(
                "MISMATCH section=%0s field=%0s exp=%0d got=%0d",
                section,
                field_name,
                expected_value,
                actual_value
            );
            printed_mismatches = printed_mismatches + 1;
        end
    end
endtask

task check_rx;
    input [255:0] field_name;
    input integer expected_value;
    input integer actual_value;
    begin
        if (actual_value !== expected_value) begin
            rx_errors = rx_errors + 1;
            print_mismatch("packet-rx", field_name, expected_value, actual_value);
        end
    end
endtask

task check_tx;
    input [255:0] field_name;
    input integer expected_value;
    input integer actual_value;
    begin
        if (actual_value !== expected_value) begin
            tx_errors = tx_errors + 1;
            print_mismatch("packet-tx", field_name, expected_value, actual_value);
        end
    end
endtask

task send_rx_byte;
    input [7:0] value;
    begin
        @(negedge clk);
        rx_byte = value;
        rx_valid = 1'b1;
        @(posedge clk);
        #1;
        rx_valid = 1'b0;
    end
endtask

task test_packet_rx;
    reg [7:0] good_checksum;
    begin
        good_checksum = input_checksum(8'hA5, 8'd1, 8'd1, 8'd5, 8'h01, 8'hC0, 8'h02, 8'h00);
        send_rx_byte(8'hA5);
        send_rx_byte(8'd1);
        send_rx_byte(8'd1);
        send_rx_byte(8'd5);
        send_rx_byte(8'h01);
        send_rx_byte(8'hC0);
        send_rx_byte(8'h02);
        send_rx_byte(8'h00);
        send_rx_byte(good_checksum);

        check_rx("packet_valid", 1, rx_packet_valid);
        check_rx("checksum_error", 0, rx_checksum_error);
        check_rx("sample_valid", 1, rx_sample_valid);
        check_rx("qc_ok", 1, rx_qc_ok);
        check_rx("hour", 5, rx_hour);
        check_rx("cams_pm25_x16", 448, rx_cams_pm25_x16);
        check_rx("pa_pm25_x16", 512, rx_pa_pm25_x16);

        send_rx_byte(8'hA5);
        send_rx_byte(8'd1);
        send_rx_byte(8'd0);
        send_rx_byte(8'd99);
        send_rx_byte(8'hFF);
        send_rx_byte(8'hF0);
        send_rx_byte(8'h00);
        send_rx_byte(8'h10);
        send_rx_byte(8'h00);

        check_rx("bad_packet_valid", 0, rx_packet_valid);
        check_rx("bad_checksum_error", 1, rx_checksum_error);
    end
endtask

task test_packet_tx;
    integer timeout;
    begin
        tx_result_valid = 1'b1;
        tx_accepted = 1'b1;
        tx_alert_level = 3'd2;
        tx_alert_state = 1'b1;
        tx_fused_pm25_x16 = 32'sd593;
        tx_bias_state_x16 = -32'sd110;

        @(negedge clk);
        tx_start_packet = 1'b1;
        @(posedge clk);
        #1;
        tx_start_packet = 1'b0;

        timeout = 0;
        while (!tx_packet_done && timeout < 200) begin
            @(posedge clk);
            #1;
            timeout = timeout + 1;
        end

        check_tx("done", 1, tx_packet_done);
        check_tx("byte_count", 10, captured_count);
        check_tx("byte0", 8'h5A, captured_tx[0]);
        check_tx("byte1", 8'd1, captured_tx[1]);
        check_tx("byte2", 8'd1, captured_tx[2]);
        check_tx("byte3", 8'd2, captured_tx[3]);
        check_tx("byte4", 8'd1, captured_tx[4]);
        check_tx("byte5", 8'h02, captured_tx[5]);
        check_tx("byte6", 8'h51, captured_tx[6]);
        check_tx("byte7", 8'hFF, captured_tx[7]);
        check_tx("byte8", 8'h92, captured_tx[8]);
        check_tx("byte9", 8'h43, captured_tx[9]);
    end
endtask

initial begin
    rx_valid = 1'b0;
    rx_byte = 8'd0;
    tx_start_packet = 1'b0;
    tx_result_valid = 1'b0;
    tx_accepted = 1'b0;
    tx_alert_level = 3'd0;
    tx_alert_state = 1'b0;
    tx_fused_pm25_x16 = 32'sd0;
    tx_bias_state_x16 = 32'sd0;
    rx_errors = 0;
    tx_errors = 0;
    printed_mismatches = 0;
    rst_n = 1'b0;

    repeat (4) @(posedge clk);
    rst_n = 1'b1;
    repeat (2) @(posedge clk);

    test_packet_rx();
    test_packet_tx();

    if (rx_errors == 0) begin
        $display("[pm25-uart] packet-rx: PASS");
    end else begin
        $display("[pm25-uart] packet-rx: FAIL errors=%0d", rx_errors);
    end

    if (tx_errors == 0) begin
        $display("[pm25-uart] packet-tx: PASS");
    end else begin
        $display("[pm25-uart] packet-tx: FAIL errors=%0d", tx_errors);
    end

    if ((rx_errors == 0) && (tx_errors == 0)) begin
        $display("[pm25-uart] summary: PASS");
        $finish;
    end else begin
        $display("[pm25-uart] summary: FAIL");
        $fatal(1);
    end
end

endmodule
