// Generic board-independent UART wrapper for the PM2.5 alert core.
module pm25_uart_demo_top #(
    parameter integer CLK_FREQ_HZ = 27000000,
    parameter integer BAUD_RATE = 115200,
    parameter integer ALPHA_SHIFT = 3
) (
    clk,
    rst_n,
    uart_rx,
    uart_tx
);

input wire clk;
input wire rst_n;
input wire uart_rx;
output wire uart_tx;

wire rx_byte_valid;
wire [7:0] rx_byte;
wire packet_valid;
// Retained for packet-integrity observability in simulation/debug. A checksum
// error never asserts packet_valid, so it cannot create a core transaction.
wire checksum_error;
wire sample_valid_to_core;
wire qc_ok_to_core;
wire [4:0] hour_to_core;
wire signed [31:0] cams_pm25_x16_to_core;
wire signed [31:0] pa_pm25_x16_to_core;
wire core_sample_ready;
wire core_result_valid;
wire core_accepted;
wire signed [31:0] core_fused_pm25_x16;
wire [2:0] core_alert_level;
wire core_alert_state_after;
wire signed [31:0] core_bias_state_x16;
wire uart_tx_busy;
wire uart_tx_start;
wire [7:0] uart_tx_data;
wire packet_tx_done;
wire request_fire;
wire core_sample_valid;

reg response_capture_pending;
reg response_pending;
reg tx_active;
reg packet_tx_start;
reg response_result_valid;
reg response_accepted;
reg [2:0] response_alert_level;
reg response_alert_state;
reg signed [31:0] response_fused_pm25_x16;
reg signed [31:0] response_bias_state_x16;

// One checksum-valid packet is accepted only while the stop-and-wait response
// path is free. Decoded sample_valid controls the core transaction, while
// request_fire independently schedules a response for invalid samples.
assign request_fire = packet_valid
                   && core_sample_ready
                   && !response_capture_pending
                   && !response_pending
                   && !tx_active;
assign core_sample_valid = request_fire && sample_valid_to_core;

uart_rx #(
    .CLK_FREQ_HZ(CLK_FREQ_HZ),
    .BAUD_RATE(BAUD_RATE)
) u_uart_rx (
    .clk(clk),
    .rst_n(rst_n),
    .rx(uart_rx),
    .data_valid(rx_byte_valid),
    .data_byte(rx_byte)
);

pm25_packet_rx u_packet_rx (
    .clk(clk),
    .rst_n(rst_n),
    .rx_valid(rx_byte_valid),
    .rx_byte(rx_byte),
    .sample_valid_out(sample_valid_to_core),
    .qc_ok_out(qc_ok_to_core),
    .hour_out(hour_to_core),
    .cams_pm25_x16_out(cams_pm25_x16_to_core),
    .pa_pm25_x16_out(pa_pm25_x16_to_core),
    .packet_valid(packet_valid),
    .checksum_error(checksum_error)
);

pm25_alert_core #(
    .ALPHA_SHIFT(ALPHA_SHIFT)
) u_core (
    .clk(clk),
    .rst_n(rst_n),
    .sample_valid(core_sample_valid),
    .qc_ok(qc_ok_to_core),
    .hour(hour_to_core),
    .cams_pm25_x16(cams_pm25_x16_to_core),
    .pa_pm25_x16(pa_pm25_x16_to_core),
    .sample_ready(core_sample_ready),
    .result_valid(core_result_valid),
    .accepted(core_accepted),
    .hour_out(),
    .bias_before_x16(),
    .residual_x16(),
    .error_x16(),
    .delta_x16(),
    .bias_after_x16(),
    .fused_raw_x16(),
    .fused_pm25_x16(core_fused_pm25_x16),
    .alert_level(core_alert_level),
    .alert_state_before(),
    .alert_state_after(core_alert_state_after),
    .bias_state_x16(core_bias_state_x16)
);

pm25_packet_tx u_packet_tx (
    .clk(clk),
    .rst_n(rst_n),
    .start(packet_tx_start),
    .result_valid(response_result_valid),
    .accepted(response_accepted),
    .alert_level(response_alert_level),
    .alert_state(response_alert_state),
    .fused_pm25_x16(response_fused_pm25_x16),
    .bias_state_x16(response_bias_state_x16),
    .tx_busy(uart_tx_busy),
    .tx_start(uart_tx_start),
    .tx_data(uart_tx_data),
    .done(packet_tx_done)
);

uart_tx #(
    .CLK_FREQ_HZ(CLK_FREQ_HZ),
    .BAUD_RATE(BAUD_RATE)
) u_uart_tx (
    .clk(clk),
    .rst_n(rst_n),
    .tx_start(uart_tx_start),
    .tx_data(uart_tx_data),
    .tx(uart_tx),
    .tx_busy(uart_tx_busy),
    .tx_done()
);

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        response_capture_pending <= 1'b0;
        response_pending <= 1'b0;
        tx_active <= 1'b0;
        packet_tx_start <= 1'b0;
        response_result_valid <= 1'b0;
        response_accepted <= 1'b0;
        response_alert_level <= 3'd0;
        response_alert_state <= 1'b0;
        response_fused_pm25_x16 <= 32'sd0;
        response_bias_state_x16 <= 32'sd0;
    end else begin
        packet_tx_start <= 1'b0;

        if (packet_tx_done) begin
            tx_active <= 1'b0;
        end

        if (request_fire) begin
            response_capture_pending <= 1'b1;
        end

        // The core registers all result/diagnostic fields on the request edge.
        // Capture them one cycle later even when core_result_valid is zero.
        if (response_capture_pending) begin
            response_result_valid <= core_result_valid;
            response_accepted <= core_accepted;
            response_alert_level <= core_alert_level;
            response_alert_state <= core_alert_state_after;
            response_fused_pm25_x16 <= core_fused_pm25_x16;
            response_bias_state_x16 <= core_bias_state_x16;
            response_pending <= 1'b1;
            response_capture_pending <= 1'b0;
        end

        if (response_pending && !tx_active && !uart_tx_busy) begin
            packet_tx_start <= 1'b1;
            tx_active <= 1'b1;
            response_pending <= 1'b0;
        end
    end
end

endmodule
