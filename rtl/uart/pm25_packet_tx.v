// Encode PM2.5 core outputs into FPGA-to-laptop binary response packets.
module pm25_packet_tx (
    clk,
    rst_n,
    start,
    result_valid,
    accepted,
    alert_level,
    alert_state,
    fused_pm25_x16,
    bias_state_x16,
    tx_busy,
    tx_start,
    tx_data,
    done
);

input clk;
input rst_n;
input start;
input result_valid;
input accepted;
input [2:0] alert_level;
input alert_state;
input signed [31:0] fused_pm25_x16;
input signed [31:0] bias_state_x16;
input tx_busy;
output reg tx_start;
output reg [7:0] tx_data;
output reg done;

localparam [7:0] START_BYTE = 8'h5A;
localparam [2:0] STATE_IDLE = 3'd0;
localparam [2:0] STATE_SEND = 3'd1;
localparam [2:0] STATE_WAIT_BUSY_HIGH = 3'd2;
localparam [2:0] STATE_WAIT_BUSY_LOW = 3'd3;
localparam [2:0] STATE_WAIT_LAST_HIGH = 3'd4;
localparam [2:0] STATE_WAIT_LAST_LOW = 3'd5;

reg [2:0] state;
reg [3:0] byte_index;
reg [7:0] packet0;
reg [7:0] packet1;
reg [7:0] packet2;
reg [7:0] packet3;
reg [7:0] packet4;
reg [7:0] packet5;
reg [7:0] packet6;
reg [7:0] packet7;
reg [7:0] packet8;
reg [7:0] packet9;

function signed [15:0] sat_int16;
    input signed [31:0] value;
    begin
        if (value > 32'sd32767) begin
            sat_int16 = 16'sh7fff;
        end else if (value < -32'sd32768) begin
            sat_int16 = 16'sh8000;
        end else begin
            sat_int16 = value[15:0];
        end
    end
endfunction

function [7:0] packet_byte;
    input [3:0] index;
    begin
        case (index)
            4'd0: packet_byte = packet0;
            4'd1: packet_byte = packet1;
            4'd2: packet_byte = packet2;
            4'd3: packet_byte = packet3;
            4'd4: packet_byte = packet4;
            4'd5: packet_byte = packet5;
            4'd6: packet_byte = packet6;
            4'd7: packet_byte = packet7;
            4'd8: packet_byte = packet8;
            default: packet_byte = packet9;
        endcase
    end
endfunction

wire signed [15:0] fused_i16;
wire signed [15:0] bias_i16;
wire [7:0] result_valid_byte;
wire [7:0] accepted_byte;
wire [7:0] alert_level_byte;
wire [7:0] alert_state_byte;
wire [7:0] checksum_byte;

assign fused_i16 = sat_int16(fused_pm25_x16);
assign bias_i16 = sat_int16(bias_state_x16);
assign result_valid_byte = {7'd0, result_valid};
assign accepted_byte = {7'd0, accepted};
assign alert_level_byte = {5'd0, alert_level};
assign alert_state_byte = {7'd0, alert_state};
assign checksum_byte = START_BYTE
                     + result_valid_byte
                     + accepted_byte
                     + alert_level_byte
                     + alert_state_byte
                     + fused_i16[15:8]
                     + fused_i16[7:0]
                     + bias_i16[15:8]
                     + bias_i16[7:0];

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        state <= STATE_IDLE;
        byte_index <= 4'd0;
        tx_start <= 1'b0;
        tx_data <= 8'd0;
        done <= 1'b0;
        packet0 <= 8'd0;
        packet1 <= 8'd0;
        packet2 <= 8'd0;
        packet3 <= 8'd0;
        packet4 <= 8'd0;
        packet5 <= 8'd0;
        packet6 <= 8'd0;
        packet7 <= 8'd0;
        packet8 <= 8'd0;
        packet9 <= 8'd0;
    end else begin
        tx_start <= 1'b0;
        done <= 1'b0;

        case (state)
            STATE_IDLE: begin
                byte_index <= 4'd0;
                if (start) begin
                    packet0 <= START_BYTE;
                    packet1 <= result_valid_byte;
                    packet2 <= accepted_byte;
                    packet3 <= alert_level_byte;
                    packet4 <= alert_state_byte;
                    packet5 <= fused_i16[15:8];
                    packet6 <= fused_i16[7:0];
                    packet7 <= bias_i16[15:8];
                    packet8 <= bias_i16[7:0];
                    packet9 <= checksum_byte;
                    state <= STATE_SEND;
                end
            end

            STATE_SEND: begin
                if (!tx_busy) begin
                    tx_data <= packet_byte(byte_index);
                    tx_start <= 1'b1;
                    if (byte_index == 4'd9) begin
                        state <= STATE_WAIT_LAST_HIGH;
                    end else begin
                        byte_index <= byte_index + 4'd1;
                        state <= STATE_WAIT_BUSY_HIGH;
                    end
                end
            end

            STATE_WAIT_BUSY_HIGH: begin
                if (tx_busy) begin
                    state <= STATE_WAIT_BUSY_LOW;
                end
            end

            STATE_WAIT_BUSY_LOW: begin
                if (!tx_busy) begin
                    state <= STATE_SEND;
                end
            end

            STATE_WAIT_LAST_HIGH: begin
                if (tx_busy) begin
                    state <= STATE_WAIT_LAST_LOW;
                end
            end

            STATE_WAIT_LAST_LOW: begin
                if (!tx_busy) begin
                    done <= 1'b1;
                    state <= STATE_IDLE;
                end
            end

            default: begin
                state <= STATE_IDLE;
            end
        endcase
    end
end

endmodule
