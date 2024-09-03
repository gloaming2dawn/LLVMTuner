; ModuleID = '/home/jiayu/result_llvmtuner_17_test1/cBench/security_sha/reduce/sha/IR-aa71c2e33f3b6a179d245f10ead9434f/sha.opt.bc'
source_filename = "sha.c"
target datalayout = "e-m:e-i8:8:32-i16:16:32-i64:64-i128:128-n32:64-S128"
target triple = "aarch64-unknown-linux-gnu"

%struct.SHA_INFO = type { [5 x i64], i64, i64, [16 x i64] }

@.str = private unnamed_addr constant [31 x i8] c"%08lx %08lx %08lx %08lx %08lx\0A\00", align 1

; Function Attrs: nounwind uwtable
define dso_local void @sha_init(ptr noundef %sha_info) #0 {
entry:
  store i64 1732584193, ptr %sha_info, align 8, !tbaa !6
  %arrayidx2 = getelementptr inbounds [5 x i64], ptr %sha_info, i64 0, i64 1
  store i64 4023233417, ptr %arrayidx2, align 8, !tbaa !6
  %arrayidx4 = getelementptr inbounds [5 x i64], ptr %sha_info, i64 0, i64 2
  store i64 2562383102, ptr %arrayidx4, align 8, !tbaa !6
  %arrayidx6 = getelementptr inbounds [5 x i64], ptr %sha_info, i64 0, i64 3
  store i64 271733878, ptr %arrayidx6, align 8, !tbaa !6
  %arrayidx8 = getelementptr inbounds [5 x i64], ptr %sha_info, i64 0, i64 4
  store i64 3285377520, ptr %arrayidx8, align 8, !tbaa !6
  %count_lo = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 1
  store i64 0, ptr %count_lo, align 8, !tbaa !10
  %count_hi = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 2
  store i64 0, ptr %count_hi, align 8, !tbaa !12
  ret void
}

; Function Attrs: nounwind uwtable
define dso_local void @sha_update(ptr noundef %sha_info, ptr noundef %buffer, i32 noundef %count) #0 {
entry:
  %count_lo = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 1
  %0 = load i64, ptr %count_lo, align 8, !tbaa !10
  %conv = sext i32 %count to i64
  %shl = shl nsw i64 %conv, 3
  %add = add i64 %0, %shl
  %cmp = icmp ult i64 %add, %0
  br i1 %cmp, label %if.then, label %if.end

if.then:                                          ; preds = %entry
  %count_hi = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 2
  %1 = load i64, ptr %count_hi, align 8, !tbaa !12
  %inc = add i64 %1, 1
  store i64 %inc, ptr %count_hi, align 8, !tbaa !12
  br label %if.end

if.end:                                           ; preds = %if.then, %entry
  store i64 %add, ptr %count_lo, align 8, !tbaa !10
  %shr = lshr i64 %conv, 29
  %count_hi8 = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 2
  %2 = load i64, ptr %count_hi8, align 8, !tbaa !12
  %add9 = add i64 %2, %shr
  store i64 %add9, ptr %count_hi8, align 8, !tbaa !12
  %cmp101 = icmp sgt i32 %count, 63
  br i1 %cmp101, label %while.body.lr.ph, label %while.end

while.body.lr.ph:                                 ; preds = %if.end
  br label %while.body

while.body:                                       ; preds = %while.body.lr.ph, %while.body
  %buffer.addr.0 = phi ptr [ %buffer, %while.body.lr.ph ], [ %add.ptr, %while.body ]
  %3 = phi i32 [ %count, %while.body.lr.ph ], [ %sub, %while.body ]
  %data = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 3
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(64) %data, ptr noundef nonnull align 1 dereferenceable(64) %buffer.addr.0, i64 64, i1 false)
  call void @byte_reverse(ptr noundef nonnull %data, i32 noundef 64)
  call void @sha_transform(ptr noundef %sha_info)
  %add.ptr = getelementptr inbounds i8, ptr %buffer.addr.0, i64 64
  %sub = add nsw i32 %3, -64
  %cmp10 = icmp sgt i32 %3, 127
  br i1 %cmp10, label %while.body, label %while.cond.while.end_crit_edge, !llvm.loop !13

while.cond.while.end_crit_edge:                   ; preds = %while.body
  br label %while.end

while.end:                                        ; preds = %while.cond.while.end_crit_edge, %if.end
  %buffer.addr.1 = phi ptr [ %add.ptr, %while.cond.while.end_crit_edge ], [ %buffer, %if.end ]
  %.lcssa = phi i32 [ %sub, %while.cond.while.end_crit_edge ], [ %count, %if.end ]
  %data14 = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 3
  %conv16 = sext i32 %.lcssa to i64
  call void @llvm.memcpy.p0.p0.i64(ptr nonnull align 8 %data14, ptr align 1 %buffer.addr.1, i64 %conv16, i1 false)
  ret void
}

; Function Attrs: nocallback nofree nounwind willreturn memory(argmem: readwrite)
declare void @llvm.memcpy.p0.p0.i64(ptr noalias nocapture writeonly, ptr noalias nocapture readonly, i64, i1 immarg) #1

; Function Attrs: nounwind uwtable
define internal void @byte_reverse(ptr noundef %buffer, i32 noundef %count) #0 {
entry:
  %conv1 = ashr i32 %count, 3
  %cmp1 = icmp sgt i32 %count, 7
  br i1 %cmp1, label %for.body.lr.ph, label %for.end

for.body.lr.ph:                                   ; preds = %entry
  br label %for.body

for.body:                                         ; preds = %for.body.lr.ph, %for.inc
  %cp.0 = phi ptr [ %buffer, %for.body.lr.ph ], [ %add.ptr, %for.inc ]
  %0 = phi i32 [ 0, %for.body.lr.ph ], [ %inc, %for.inc ]
  %1 = load i8, ptr %cp.0, align 1, !tbaa !15
  %arrayidx4 = getelementptr inbounds i8, ptr %cp.0, i64 1
  %2 = load i8, ptr %arrayidx4, align 1, !tbaa !15
  %arrayidx6 = getelementptr inbounds i8, ptr %cp.0, i64 2
  %3 = load i8, ptr %arrayidx6, align 1, !tbaa !15
  %arrayidx8 = getelementptr inbounds i8, ptr %cp.0, i64 3
  %4 = load i8, ptr %arrayidx8, align 1, !tbaa !15
  store i8 %4, ptr %cp.0, align 1, !tbaa !15
  store i8 %3, ptr %arrayidx4, align 1, !tbaa !15
  store i8 %2, ptr %arrayidx6, align 1, !tbaa !15
  store i8 %1, ptr %arrayidx8, align 1, !tbaa !15
  %add.ptr = getelementptr inbounds i8, ptr %cp.0, i64 8
  br label %for.inc

for.inc:                                          ; preds = %for.body
  %inc = add nuw nsw i32 %0, 1
  %cmp = icmp slt i32 %inc, %conv1
  br i1 %cmp, label %for.body, label %for.cond.for.end_crit_edge, !llvm.loop !16

for.cond.for.end_crit_edge:                       ; preds = %for.inc
  br label %for.end

for.end:                                          ; preds = %for.cond.for.end_crit_edge, %entry
  ret void
}

; Function Attrs: nounwind uwtable
define internal void @sha_transform(ptr noundef %sha_info) #0 {
entry:
  %W = alloca [80 x i64], align 8
  call void @llvm.lifetime.start.p0(i64 640, ptr nonnull %W) #5
  br i1 true, label %for.body.lr.ph, label %for.end

for.body.lr.ph:                                   ; preds = %entry
  br label %for.body

for.body:                                         ; preds = %for.body.lr.ph, %for.inc
  %0 = phi i32 [ 0, %for.body.lr.ph ], [ %inc, %for.inc ]
  %idxprom = zext i32 %0 to i64
  %arrayidx = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 3, i64 %idxprom
  %1 = load i64, ptr %arrayidx, align 8, !tbaa !6
  %arrayidx2 = getelementptr inbounds [80 x i64], ptr %W, i64 0, i64 %idxprom
  store i64 %1, ptr %arrayidx2, align 8, !tbaa !6
  br label %for.inc

for.inc:                                          ; preds = %for.body
  %inc = add nuw nsw i32 %0, 1
  %cmp = icmp ult i32 %0, 15
  br i1 %cmp, label %for.body, label %for.cond.for.end_crit_edge, !llvm.loop !17

for.cond.for.end_crit_edge:                       ; preds = %for.inc
  br label %for.end

for.end:                                          ; preds = %for.cond.for.end_crit_edge, %entry
  br i1 true, label %for.body5.lr.ph, label %for.end23

for.body5.lr.ph:                                  ; preds = %for.end
  br label %for.body5

for.body5:                                        ; preds = %for.body5.lr.ph, %for.inc21
  %2 = phi i32 [ 16, %for.body5.lr.ph ], [ %inc22, %for.inc21 ]
  %sub = add nsw i32 %2, -3
  %idxprom6 = sext i32 %sub to i64
  %arrayidx7 = getelementptr inbounds [80 x i64], ptr %W, i64 0, i64 %idxprom6
  %3 = load i64, ptr %arrayidx7, align 8, !tbaa !6
  %sub8 = add nsw i32 %2, -8
  %idxprom9 = sext i32 %sub8 to i64
  %arrayidx10 = getelementptr inbounds [80 x i64], ptr %W, i64 0, i64 %idxprom9
  %4 = load i64, ptr %arrayidx10, align 8, !tbaa !6
  %xor = xor i64 %3, %4
  %sub11 = add nsw i32 %2, -14
  %idxprom12 = sext i32 %sub11 to i64
  %arrayidx13 = getelementptr inbounds [80 x i64], ptr %W, i64 0, i64 %idxprom12
  %5 = load i64, ptr %arrayidx13, align 8, !tbaa !6
  %xor14 = xor i64 %xor, %5
  %sub15 = add nsw i32 %2, -16
  %idxprom16 = sext i32 %sub15 to i64
  %arrayidx17 = getelementptr inbounds [80 x i64], ptr %W, i64 0, i64 %idxprom16
  %6 = load i64, ptr %arrayidx17, align 8, !tbaa !6
  %xor18 = xor i64 %xor14, %6
  %idxprom19 = zext i32 %2 to i64
  %arrayidx20 = getelementptr inbounds [80 x i64], ptr %W, i64 0, i64 %idxprom19
  store i64 %xor18, ptr %arrayidx20, align 8, !tbaa !6
  br label %for.inc21

for.inc21:                                        ; preds = %for.body5
  %inc22 = add nuw nsw i32 %2, 1
  %cmp4 = icmp ult i32 %2, 79
  br i1 %cmp4, label %for.body5, label %for.cond3.for.end23_crit_edge, !llvm.loop !18

for.cond3.for.end23_crit_edge:                    ; preds = %for.inc21
  br label %for.end23

for.end23:                                        ; preds = %for.cond3.for.end23_crit_edge, %for.end
  %7 = load i64, ptr %sha_info, align 8, !tbaa !6
  %arrayidx26 = getelementptr inbounds [5 x i64], ptr %sha_info, i64 0, i64 1
  %8 = load i64, ptr %arrayidx26, align 8, !tbaa !6
  %arrayidx28 = getelementptr inbounds [5 x i64], ptr %sha_info, i64 0, i64 2
  %9 = load i64, ptr %arrayidx28, align 8, !tbaa !6
  %arrayidx30 = getelementptr inbounds [5 x i64], ptr %sha_info, i64 0, i64 3
  %10 = load i64, ptr %arrayidx30, align 8, !tbaa !6
  %arrayidx32 = getelementptr inbounds [5 x i64], ptr %sha_info, i64 0, i64 4
  %11 = load i64, ptr %arrayidx32, align 8, !tbaa !6
  br i1 true, label %for.body35.lr.ph, label %for.end48

for.body35.lr.ph:                                 ; preds = %for.end23
  br label %for.body35

for.body35:                                       ; preds = %for.body35.lr.ph, %for.inc46
  %A.0 = phi i64 [ %7, %for.body35.lr.ph ], [ %add42, %for.inc46 ]
  %B.0 = phi i64 [ %8, %for.body35.lr.ph ], [ %A.0, %for.inc46 ]
  %C.0 = phi i64 [ %9, %for.body35.lr.ph ], [ %or45, %for.inc46 ]
  %D.0 = phi i64 [ %10, %for.body35.lr.ph ], [ %C.0, %for.inc46 ]
  %E.0 = phi i64 [ %11, %for.body35.lr.ph ], [ %D.0, %for.inc46 ]
  %12 = phi i32 [ 0, %for.body35.lr.ph ], [ %inc47, %for.inc46 ]
  %shl = shl i64 %A.0, 5
  %shr = lshr i64 %A.0, 27
  %or = or i64 %shl, %shr
  %and = and i64 %B.0, %C.0
  %not = xor i64 %B.0, -1
  %and36 = and i64 %D.0, %not
  %or37 = or i64 %and, %and36
  %add = add i64 %or, %or37
  %add38 = add i64 %add, %E.0
  %idxprom39 = zext i32 %12 to i64
  %arrayidx40 = getelementptr inbounds [80 x i64], ptr %W, i64 0, i64 %idxprom39
  %13 = load i64, ptr %arrayidx40, align 8, !tbaa !6
  %add41 = add i64 %add38, %13
  %add42 = add i64 %add41, 1518500249
  %shl43 = shl i64 %B.0, 30
  %shr44 = lshr i64 %B.0, 2
  %or45 = or i64 %shl43, %shr44
  br label %for.inc46

for.inc46:                                        ; preds = %for.body35
  %inc47 = add nuw nsw i32 %12, 1
  %cmp34 = icmp ult i32 %12, 19
  br i1 %cmp34, label %for.body35, label %for.cond33.for.end48_crit_edge, !llvm.loop !19

for.cond33.for.end48_crit_edge:                   ; preds = %for.inc46
  br label %for.end48

for.end48:                                        ; preds = %for.cond33.for.end48_crit_edge, %for.end23
  %A.1 = phi i64 [ %add42, %for.cond33.for.end48_crit_edge ], [ %7, %for.end23 ]
  %B.1 = phi i64 [ %A.0, %for.cond33.for.end48_crit_edge ], [ %8, %for.end23 ]
  %C.1 = phi i64 [ %or45, %for.cond33.for.end48_crit_edge ], [ %9, %for.end23 ]
  %D.1 = phi i64 [ %C.0, %for.cond33.for.end48_crit_edge ], [ %10, %for.end23 ]
  %E.1 = phi i64 [ %D.0, %for.cond33.for.end48_crit_edge ], [ %11, %for.end23 ]
  br i1 true, label %for.body51.lr.ph, label %for.end68

for.body51.lr.ph:                                 ; preds = %for.end48
  br label %for.body51

for.body51:                                       ; preds = %for.body51.lr.ph, %for.inc66
  %A.2 = phi i64 [ %A.1, %for.body51.lr.ph ], [ %add62, %for.inc66 ]
  %B.2 = phi i64 [ %B.1, %for.body51.lr.ph ], [ %A.2, %for.inc66 ]
  %C.2 = phi i64 [ %C.1, %for.body51.lr.ph ], [ %or65, %for.inc66 ]
  %D.2 = phi i64 [ %D.1, %for.body51.lr.ph ], [ %C.2, %for.inc66 ]
  %E.2 = phi i64 [ %E.1, %for.body51.lr.ph ], [ %D.2, %for.inc66 ]
  %14 = phi i32 [ 20, %for.body51.lr.ph ], [ %inc67, %for.inc66 ]
  %shl52 = shl i64 %A.2, 5
  %shr53 = lshr i64 %A.2, 27
  %or54 = or i64 %shl52, %shr53
  %xor55 = xor i64 %B.2, %C.2
  %xor56 = xor i64 %xor55, %D.2
  %add57 = add i64 %or54, %xor56
  %add58 = add i64 %add57, %E.2
  %idxprom59 = zext i32 %14 to i64
  %arrayidx60 = getelementptr inbounds [80 x i64], ptr %W, i64 0, i64 %idxprom59
  %15 = load i64, ptr %arrayidx60, align 8, !tbaa !6
  %add61 = add i64 %add58, %15
  %add62 = add i64 %add61, 1859775393
  %shl63 = shl i64 %B.2, 30
  %shr64 = lshr i64 %B.2, 2
  %or65 = or i64 %shl63, %shr64
  br label %for.inc66

for.inc66:                                        ; preds = %for.body51
  %inc67 = add nuw nsw i32 %14, 1
  %cmp50 = icmp ult i32 %14, 39
  br i1 %cmp50, label %for.body51, label %for.cond49.for.end68_crit_edge, !llvm.loop !20

for.cond49.for.end68_crit_edge:                   ; preds = %for.inc66
  br label %for.end68

for.end68:                                        ; preds = %for.cond49.for.end68_crit_edge, %for.end48
  %A.3 = phi i64 [ %add62, %for.cond49.for.end68_crit_edge ], [ %A.1, %for.end48 ]
  %B.3 = phi i64 [ %A.2, %for.cond49.for.end68_crit_edge ], [ %B.1, %for.end48 ]
  %C.3 = phi i64 [ %or65, %for.cond49.for.end68_crit_edge ], [ %C.1, %for.end48 ]
  %D.3 = phi i64 [ %C.2, %for.cond49.for.end68_crit_edge ], [ %D.1, %for.end48 ]
  %E.3 = phi i64 [ %D.2, %for.cond49.for.end68_crit_edge ], [ %E.1, %for.end48 ]
  br i1 true, label %for.body71.lr.ph, label %for.end91

for.body71.lr.ph:                                 ; preds = %for.end68
  br label %for.body71

for.body71:                                       ; preds = %for.body71.lr.ph, %for.inc89
  %A.4 = phi i64 [ %A.3, %for.body71.lr.ph ], [ %add85, %for.inc89 ]
  %B.4 = phi i64 [ %B.3, %for.body71.lr.ph ], [ %A.4, %for.inc89 ]
  %C.4 = phi i64 [ %C.3, %for.body71.lr.ph ], [ %or88, %for.inc89 ]
  %D.4 = phi i64 [ %D.3, %for.body71.lr.ph ], [ %C.4, %for.inc89 ]
  %E.4 = phi i64 [ %E.3, %for.body71.lr.ph ], [ %D.4, %for.inc89 ]
  %16 = phi i32 [ 40, %for.body71.lr.ph ], [ %inc90, %for.inc89 ]
  %shl72 = shl i64 %A.4, 5
  %shr73 = lshr i64 %A.4, 27
  %or74 = or i64 %shl72, %shr73
  %and767 = or i64 %C.4, %D.4
  %or77 = and i64 %B.4, %and767
  %and78 = and i64 %C.4, %D.4
  %or79 = or i64 %or77, %and78
  %add80 = add i64 %or74, %or79
  %add81 = add i64 %add80, %E.4
  %idxprom82 = zext i32 %16 to i64
  %arrayidx83 = getelementptr inbounds [80 x i64], ptr %W, i64 0, i64 %idxprom82
  %17 = load i64, ptr %arrayidx83, align 8, !tbaa !6
  %add84 = add i64 %add81, %17
  %add85 = add i64 %add84, 2400959708
  %shl86 = shl i64 %B.4, 30
  %shr87 = lshr i64 %B.4, 2
  %or88 = or i64 %shl86, %shr87
  br label %for.inc89

for.inc89:                                        ; preds = %for.body71
  %inc90 = add nuw nsw i32 %16, 1
  %cmp70 = icmp ult i32 %16, 59
  br i1 %cmp70, label %for.body71, label %for.cond69.for.end91_crit_edge, !llvm.loop !21

for.cond69.for.end91_crit_edge:                   ; preds = %for.inc89
  br label %for.end91

for.end91:                                        ; preds = %for.cond69.for.end91_crit_edge, %for.end68
  %A.5 = phi i64 [ %add85, %for.cond69.for.end91_crit_edge ], [ %A.3, %for.end68 ]
  %B.5 = phi i64 [ %A.4, %for.cond69.for.end91_crit_edge ], [ %B.3, %for.end68 ]
  %C.5 = phi i64 [ %or88, %for.cond69.for.end91_crit_edge ], [ %C.3, %for.end68 ]
  %D.5 = phi i64 [ %C.4, %for.cond69.for.end91_crit_edge ], [ %D.3, %for.end68 ]
  %E.5 = phi i64 [ %D.4, %for.cond69.for.end91_crit_edge ], [ %E.3, %for.end68 ]
  br i1 true, label %for.body94.lr.ph, label %for.end111

for.body94.lr.ph:                                 ; preds = %for.end91
  br label %for.body94

for.body94:                                       ; preds = %for.body94.lr.ph, %for.inc109
  %A.6 = phi i64 [ %A.5, %for.body94.lr.ph ], [ %add105, %for.inc109 ]
  %B.6 = phi i64 [ %B.5, %for.body94.lr.ph ], [ %A.6, %for.inc109 ]
  %C.6 = phi i64 [ %C.5, %for.body94.lr.ph ], [ %or108, %for.inc109 ]
  %D.6 = phi i64 [ %D.5, %for.body94.lr.ph ], [ %C.6, %for.inc109 ]
  %E.6 = phi i64 [ %E.5, %for.body94.lr.ph ], [ %D.6, %for.inc109 ]
  %18 = phi i32 [ 60, %for.body94.lr.ph ], [ %inc110, %for.inc109 ]
  %shl95 = shl i64 %A.6, 5
  %shr96 = lshr i64 %A.6, 27
  %or97 = or i64 %shl95, %shr96
  %xor98 = xor i64 %B.6, %C.6
  %xor99 = xor i64 %xor98, %D.6
  %add100 = add i64 %or97, %xor99
  %add101 = add i64 %add100, %E.6
  %idxprom102 = zext i32 %18 to i64
  %arrayidx103 = getelementptr inbounds [80 x i64], ptr %W, i64 0, i64 %idxprom102
  %19 = load i64, ptr %arrayidx103, align 8, !tbaa !6
  %add104 = add i64 %add101, %19
  %add105 = add i64 %add104, 3395469782
  %shl106 = shl i64 %B.6, 30
  %shr107 = lshr i64 %B.6, 2
  %or108 = or i64 %shl106, %shr107
  br label %for.inc109

for.inc109:                                       ; preds = %for.body94
  %inc110 = add nuw nsw i32 %18, 1
  %cmp93 = icmp ult i32 %18, 79
  br i1 %cmp93, label %for.body94, label %for.cond92.for.end111_crit_edge, !llvm.loop !22

for.cond92.for.end111_crit_edge:                  ; preds = %for.inc109
  br label %for.end111

for.end111:                                       ; preds = %for.cond92.for.end111_crit_edge, %for.end91
  %A.7 = phi i64 [ %add105, %for.cond92.for.end111_crit_edge ], [ %A.5, %for.end91 ]
  %B.7 = phi i64 [ %A.6, %for.cond92.for.end111_crit_edge ], [ %B.5, %for.end91 ]
  %C.7 = phi i64 [ %or108, %for.cond92.for.end111_crit_edge ], [ %C.5, %for.end91 ]
  %D.7 = phi i64 [ %C.6, %for.cond92.for.end111_crit_edge ], [ %D.5, %for.end91 ]
  %E.7 = phi i64 [ %D.6, %for.cond92.for.end111_crit_edge ], [ %E.5, %for.end91 ]
  %add114 = add i64 %7, %A.7
  store i64 %add114, ptr %sha_info, align 8, !tbaa !6
  %add117 = add i64 %8, %B.7
  store i64 %add117, ptr %arrayidx26, align 8, !tbaa !6
  %add120 = add i64 %9, %C.7
  store i64 %add120, ptr %arrayidx28, align 8, !tbaa !6
  %add123 = add i64 %10, %D.7
  store i64 %add123, ptr %arrayidx30, align 8, !tbaa !6
  %add126 = add i64 %11, %E.7
  store i64 %add126, ptr %arrayidx32, align 8, !tbaa !6
  call void @llvm.lifetime.end.p0(i64 640, ptr nonnull %W) #5
  ret void
}

; Function Attrs: nounwind uwtable
define dso_local void @sha_final(ptr noundef %sha_info) #0 {
entry:
  %count_lo = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 1
  %0 = load i64, ptr %count_lo, align 8, !tbaa !10
  %count_hi = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 2
  %1 = load i64, ptr %count_hi, align 8, !tbaa !12
  %2 = trunc i64 %0 to i32
  %3 = lshr i32 %2, 3
  %conv = and i32 %3, 63
  %data = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 3
  %inc = add nuw nsw i32 %conv, 1
  %idxprom = zext i32 %conv to i64
  %arrayidx = getelementptr inbounds i8, ptr %data, i64 %idxprom
  store i8 -128, ptr %arrayidx, align 1, !tbaa !15
  %cmp = icmp ugt i32 %conv, 55
  br i1 %cmp, label %if.then, label %if.else

if.then:                                          ; preds = %entry
  %idx.ext = zext i32 %inc to i64
  %add.ptr = getelementptr inbounds i8, ptr %data, i64 %idx.ext
  %sub = xor i32 %conv, 63
  %conv3 = zext i32 %sub to i64
  call void @llvm.memset.p0.i64(ptr nonnull align 1 %add.ptr, i8 0, i64 %conv3, i1 false)
  call void @byte_reverse(ptr noundef nonnull %data, i32 noundef 64)
  call void @sha_transform(ptr noundef %sha_info)
  call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(56) %data, i8 0, i64 56, i1 false)
  br label %if.end

if.else:                                          ; preds = %entry
  %idx.ext8 = zext i32 %inc to i64
  %add.ptr9 = getelementptr inbounds i8, ptr %data, i64 %idx.ext8
  %sub10 = sub nsw i32 55, %conv
  %conv11 = sext i32 %sub10 to i64
  call void @llvm.memset.p0.i64(ptr nonnull align 1 %add.ptr9, i8 0, i64 %conv11, i1 false)
  br label %if.end

if.end:                                           ; preds = %if.else, %if.then
  call void @byte_reverse(ptr noundef nonnull %data, i32 noundef 64)
  %arrayidx15 = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 3, i64 14
  store i64 %1, ptr %arrayidx15, align 8, !tbaa !6
  %arrayidx17 = getelementptr inbounds %struct.SHA_INFO, ptr %sha_info, i64 0, i32 3, i64 15
  store i64 %0, ptr %arrayidx17, align 8, !tbaa !6
  call void @sha_transform(ptr noundef %sha_info)
  ret void
}

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.start.p0(i64 immarg, ptr nocapture) #2

; Function Attrs: nocallback nofree nounwind willreturn memory(argmem: write)
declare void @llvm.memset.p0.i64(ptr nocapture writeonly, i8, i64, i1 immarg) #3

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.end.p0(i64 immarg, ptr nocapture) #2

; Function Attrs: nounwind uwtable
define dso_local void @sha_stream(ptr noundef %sha_info, ptr noundef %fin) #0 {
entry:
  %data = alloca [8192 x i8], align 1
  call void @llvm.lifetime.start.p0(i64 8192, ptr nonnull %data) #5
  call void @sha_init(ptr noundef %sha_info)
  %call1 = call i64 @fread(ptr noundef nonnull %data, i64 noundef 1, i64 noundef 8192, ptr noundef %fin) #5
  %conv2 = trunc i64 %call1 to i32
  %cmp3 = icmp sgt i32 %conv2, 0
  br i1 %cmp3, label %while.body.lr.ph, label %while.end

while.body.lr.ph:                                 ; preds = %entry
  br label %while.body

while.body:                                       ; preds = %while.body.lr.ph, %while.body
  %conv4 = phi i32 [ %conv2, %while.body.lr.ph ], [ %conv, %while.body ]
  call void @sha_update(ptr noundef %sha_info, ptr noundef nonnull %data, i32 noundef %conv4)
  %call = call i64 @fread(ptr noundef nonnull %data, i64 noundef 1, i64 noundef 8192, ptr noundef %fin) #5
  %conv = trunc i64 %call to i32
  %cmp = icmp sgt i32 %conv, 0
  br i1 %cmp, label %while.body, label %while.cond.while.end_crit_edge, !llvm.loop !23

while.cond.while.end_crit_edge:                   ; preds = %while.body
  br label %while.end

while.end:                                        ; preds = %while.cond.while.end_crit_edge, %entry
  call void @sha_final(ptr noundef %sha_info)
  call void @llvm.lifetime.end.p0(i64 8192, ptr nonnull %data) #5
  ret void
}

declare i64 @fread(ptr noundef, i64 noundef, i64 noundef, ptr noundef) #4

; Function Attrs: nounwind uwtable
define dso_local void @sha_print(ptr noundef %sha_info) #0 {
entry:
  %0 = load i64, ptr %sha_info, align 8, !tbaa !6
  %arrayidx2 = getelementptr inbounds [5 x i64], ptr %sha_info, i64 0, i64 1
  %1 = load i64, ptr %arrayidx2, align 8, !tbaa !6
  %arrayidx4 = getelementptr inbounds [5 x i64], ptr %sha_info, i64 0, i64 2
  %2 = load i64, ptr %arrayidx4, align 8, !tbaa !6
  %arrayidx6 = getelementptr inbounds [5 x i64], ptr %sha_info, i64 0, i64 3
  %3 = load i64, ptr %arrayidx6, align 8, !tbaa !6
  %arrayidx8 = getelementptr inbounds [5 x i64], ptr %sha_info, i64 0, i64 4
  %4 = load i64, ptr %arrayidx8, align 8, !tbaa !6
  %call = call i32 (ptr, ...) @printf(ptr noundef nonnull dereferenceable(1) @.str, i64 noundef %0, i64 noundef %1, i64 noundef %2, i64 noundef %3, i64 noundef %4) #5
  ret void
}

declare i32 @printf(ptr noundef, ...) #4

attributes #0 = { nounwind uwtable "frame-pointer"="non-leaf" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+fp-armv8,+neon,+v8a,-fmv" }
attributes #1 = { nocallback nofree nounwind willreturn memory(argmem: readwrite) }
attributes #2 = { nocallback nofree nosync nounwind willreturn memory(argmem: readwrite) }
attributes #3 = { nocallback nofree nounwind willreturn memory(argmem: write) }
attributes #4 = { "frame-pointer"="non-leaf" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+fp-armv8,+neon,+v8a,-fmv" }
attributes #5 = { nounwind }

!llvm.module.flags = !{!0, !1, !2, !3, !4}
!llvm.ident = !{!5}

!0 = !{i32 1, !"wchar_size", i32 4}
!1 = !{i32 8, !"PIC Level", i32 2}
!2 = !{i32 7, !"PIE Level", i32 2}
!3 = !{i32 7, !"uwtable", i32 2}
!4 = !{i32 7, !"frame-pointer", i32 1}
!5 = !{!"clang version 17.0.6 (https://github.com/llvm/llvm-project.git 6009708b4367171ccdbf4b5905cb6a803753fe18)"}
!6 = !{!7, !7, i64 0}
!7 = !{!"long", !8, i64 0}
!8 = !{!"omnipotent char", !9, i64 0}
!9 = !{!"Simple C/C++ TBAA"}
!10 = !{!11, !7, i64 40}
!11 = !{!"", !8, i64 0, !7, i64 40, !7, i64 48, !8, i64 56}
!12 = !{!11, !7, i64 48}
!13 = distinct !{!13, !14}
!14 = !{!"llvm.loop.mustprogress"}
!15 = !{!8, !8, i64 0}
!16 = distinct !{!16, !14}
!17 = distinct !{!17, !14}
!18 = distinct !{!18, !14}
!19 = distinct !{!19, !14}
!20 = distinct !{!20, !14}
!21 = distinct !{!21, !14}
!22 = distinct !{!22, !14}
!23 = distinct !{!23, !14}
