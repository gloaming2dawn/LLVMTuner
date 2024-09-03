; ModuleID = 'test.c'
source_filename = "test.c"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-gnu"

@.str = private unnamed_addr constant [10 x i8] c"A = %08x\0A\00", align 1
@.str.1 = private unnamed_addr constant [10 x i8] c"B = %08x\0A\00", align 1
@.str.2 = private unnamed_addr constant [10 x i8] c"C = %08x\0A\00", align 1
@.str.3 = private unnamed_addr constant [10 x i8] c"D = %08x\0A\00", align 1
@.str.4 = private unnamed_addr constant [10 x i8] c"E = %08x\0A\00", align 1

; Function Attrs: nounwind uwtable
define dso_local i32 @main() #0 {
entry:
  %retval = alloca i32, align 4
  %A = alloca i32, align 4
  %B = alloca i32, align 4
  %C = alloca i32, align 4
  %D = alloca i32, align 4
  %E = alloca i32, align 4
  %temp = alloca i32, align 4
  %W = alloca [80 x i32], align 16
  %i = alloca i32, align 4
  store i32 0, ptr %retval, align 4
  call void @llvm.lifetime.start.p0(i64 4, ptr %A) #3
  call void @llvm.lifetime.start.p0(i64 4, ptr %B) #3
  call void @llvm.lifetime.start.p0(i64 4, ptr %C) #3
  call void @llvm.lifetime.start.p0(i64 4, ptr %D) #3
  call void @llvm.lifetime.start.p0(i64 4, ptr %E) #3
  call void @llvm.lifetime.start.p0(i64 4, ptr %temp) #3
  call void @llvm.lifetime.start.p0(i64 320, ptr %W) #3
  call void @llvm.lifetime.start.p0(i64 4, ptr %i) #3
  store i32 1732584193, ptr %A, align 4, !tbaa !5
  store i32 -271733879, ptr %B, align 4, !tbaa !5
  store i32 -1732584194, ptr %C, align 4, !tbaa !5
  store i32 271733878, ptr %D, align 4, !tbaa !5
  store i32 -1009589776, ptr %E, align 4, !tbaa !5
  store i32 0, ptr %i, align 4, !tbaa !5
  br label %for.cond

for.cond:                                         ; preds = %for.inc, %entry
  %0 = load i32, ptr %i, align 4, !tbaa !5
  %cmp = icmp slt i32 %0, 80
  br i1 %cmp, label %for.body, label %for.end

for.body:                                         ; preds = %for.cond
  %1 = load i32, ptr %i, align 4, !tbaa !5
  %2 = load i32, ptr %i, align 4, !tbaa !5
  %idxprom = sext i32 %2 to i64
  %arrayidx = getelementptr inbounds [80 x i32], ptr %W, i64 0, i64 %idxprom
  store i32 %1, ptr %arrayidx, align 4, !tbaa !5
  br label %for.inc

for.inc:                                          ; preds = %for.body
  %3 = load i32, ptr %i, align 4, !tbaa !5
  %inc = add nsw i32 %3, 1
  store i32 %inc, ptr %i, align 4, !tbaa !5
  br label %for.cond, !llvm.loop !9

for.end:                                          ; preds = %for.cond
  store i32 0, ptr %i, align 4, !tbaa !5
  br label %for.cond1

for.cond1:                                        ; preds = %for.inc15, %for.end
  %4 = load i32, ptr %i, align 4, !tbaa !5
  %cmp2 = icmp slt i32 %4, 20
  br i1 %cmp2, label %for.body3, label %for.end17

for.body3:                                        ; preds = %for.cond1
  %5 = load i32, ptr %A, align 4, !tbaa !5
  %shl = shl i32 %5, 5
  %6 = load i32, ptr %A, align 4, !tbaa !5
  %shr = lshr i32 %6, 27
  %or = or i32 %shl, %shr
  %7 = load i32, ptr %B, align 4, !tbaa !5
  %8 = load i32, ptr %C, align 4, !tbaa !5
  %and = and i32 %7, %8
  %9 = load i32, ptr %B, align 4, !tbaa !5
  %not = xor i32 %9, -1
  %10 = load i32, ptr %D, align 4, !tbaa !5
  %and4 = and i32 %not, %10
  %or5 = or i32 %and, %and4
  %add = add i32 %or, %or5
  %11 = load i32, ptr %E, align 4, !tbaa !5
  %add6 = add i32 %add, %11
  %12 = load i32, ptr %i, align 4, !tbaa !5
  %idxprom7 = sext i32 %12 to i64
  %arrayidx8 = getelementptr inbounds [80 x i32], ptr %W, i64 0, i64 %idxprom7
  %13 = load i32, ptr %arrayidx8, align 4, !tbaa !5
  %add9 = add i32 %add6, %13
  %conv = zext i32 %add9 to i64
  %add10 = add nsw i64 %conv, 1518500249
  %conv11 = trunc i64 %add10 to i32
  store i32 %conv11, ptr %temp, align 4, !tbaa !5
  %14 = load i32, ptr %D, align 4, !tbaa !5
  store i32 %14, ptr %E, align 4, !tbaa !5
  %15 = load i32, ptr %C, align 4, !tbaa !5
  store i32 %15, ptr %D, align 4, !tbaa !5
  %16 = load i32, ptr %B, align 4, !tbaa !5
  %shl12 = shl i32 %16, 30
  %17 = load i32, ptr %B, align 4, !tbaa !5
  %shr13 = lshr i32 %17, 2
  %or14 = or i32 %shl12, %shr13
  store i32 %or14, ptr %C, align 4, !tbaa !5
  %18 = load i32, ptr %A, align 4, !tbaa !5
  store i32 %18, ptr %B, align 4, !tbaa !5
  %19 = load i32, ptr %temp, align 4, !tbaa !5
  store i32 %19, ptr %A, align 4, !tbaa !5
  br label %for.inc15

for.inc15:                                        ; preds = %for.body3
  %20 = load i32, ptr %i, align 4, !tbaa !5
  %inc16 = add nsw i32 %20, 1
  store i32 %inc16, ptr %i, align 4, !tbaa !5
  br label %for.cond1, !llvm.loop !11

for.end17:                                        ; preds = %for.cond1
  store i32 20, ptr %i, align 4, !tbaa !5
  br label %for.cond18

for.cond18:                                       ; preds = %for.inc37, %for.end17
  %21 = load i32, ptr %i, align 4, !tbaa !5
  %cmp19 = icmp slt i32 %21, 40
  br i1 %cmp19, label %for.body21, label %for.end39

for.body21:                                       ; preds = %for.cond18
  %22 = load i32, ptr %A, align 4, !tbaa !5
  %shl22 = shl i32 %22, 5
  %23 = load i32, ptr %A, align 4, !tbaa !5
  %shr23 = lshr i32 %23, 27
  %or24 = or i32 %shl22, %shr23
  %24 = load i32, ptr %B, align 4, !tbaa !5
  %25 = load i32, ptr %C, align 4, !tbaa !5
  %xor = xor i32 %24, %25
  %26 = load i32, ptr %D, align 4, !tbaa !5
  %xor25 = xor i32 %xor, %26
  %add26 = add i32 %or24, %xor25
  %27 = load i32, ptr %E, align 4, !tbaa !5
  %add27 = add i32 %add26, %27
  %28 = load i32, ptr %i, align 4, !tbaa !5
  %idxprom28 = sext i32 %28 to i64
  %arrayidx29 = getelementptr inbounds [80 x i32], ptr %W, i64 0, i64 %idxprom28
  %29 = load i32, ptr %arrayidx29, align 4, !tbaa !5
  %add30 = add i32 %add27, %29
  %conv31 = zext i32 %add30 to i64
  %add32 = add nsw i64 %conv31, 1859775393
  %conv33 = trunc i64 %add32 to i32
  store i32 %conv33, ptr %temp, align 4, !tbaa !5
  %30 = load i32, ptr %D, align 4, !tbaa !5
  store i32 %30, ptr %E, align 4, !tbaa !5
  %31 = load i32, ptr %C, align 4, !tbaa !5
  store i32 %31, ptr %D, align 4, !tbaa !5
  %32 = load i32, ptr %B, align 4, !tbaa !5
  %shl34 = shl i32 %32, 30
  %33 = load i32, ptr %B, align 4, !tbaa !5
  %shr35 = lshr i32 %33, 2
  %or36 = or i32 %shl34, %shr35
  store i32 %or36, ptr %C, align 4, !tbaa !5
  %34 = load i32, ptr %A, align 4, !tbaa !5
  store i32 %34, ptr %B, align 4, !tbaa !5
  %35 = load i32, ptr %temp, align 4, !tbaa !5
  store i32 %35, ptr %A, align 4, !tbaa !5
  br label %for.inc37

for.inc37:                                        ; preds = %for.body21
  %36 = load i32, ptr %i, align 4, !tbaa !5
  %inc38 = add nsw i32 %36, 1
  store i32 %inc38, ptr %i, align 4, !tbaa !5
  br label %for.cond18, !llvm.loop !12

for.end39:                                        ; preds = %for.cond18
  store i32 40, ptr %i, align 4, !tbaa !5
  br label %for.cond40

for.cond40:                                       ; preds = %for.inc63, %for.end39
  %37 = load i32, ptr %i, align 4, !tbaa !5
  %cmp41 = icmp slt i32 %37, 60
  br i1 %cmp41, label %for.body43, label %for.end65

for.body43:                                       ; preds = %for.cond40
  %38 = load i32, ptr %A, align 4, !tbaa !5
  %shl44 = shl i32 %38, 5
  %39 = load i32, ptr %A, align 4, !tbaa !5
  %shr45 = lshr i32 %39, 27
  %or46 = or i32 %shl44, %shr45
  %40 = load i32, ptr %B, align 4, !tbaa !5
  %41 = load i32, ptr %C, align 4, !tbaa !5
  %and47 = and i32 %40, %41
  %42 = load i32, ptr %B, align 4, !tbaa !5
  %43 = load i32, ptr %D, align 4, !tbaa !5
  %and48 = and i32 %42, %43
  %or49 = or i32 %and47, %and48
  %44 = load i32, ptr %C, align 4, !tbaa !5
  %45 = load i32, ptr %D, align 4, !tbaa !5
  %and50 = and i32 %44, %45
  %or51 = or i32 %or49, %and50
  %add52 = add i32 %or46, %or51
  %46 = load i32, ptr %E, align 4, !tbaa !5
  %add53 = add i32 %add52, %46
  %47 = load i32, ptr %i, align 4, !tbaa !5
  %idxprom54 = sext i32 %47 to i64
  %arrayidx55 = getelementptr inbounds [80 x i32], ptr %W, i64 0, i64 %idxprom54
  %48 = load i32, ptr %arrayidx55, align 4, !tbaa !5
  %add56 = add i32 %add53, %48
  %conv57 = zext i32 %add56 to i64
  %add58 = add nsw i64 %conv57, 2400959708
  %conv59 = trunc i64 %add58 to i32
  store i32 %conv59, ptr %temp, align 4, !tbaa !5
  %49 = load i32, ptr %D, align 4, !tbaa !5
  store i32 %49, ptr %E, align 4, !tbaa !5
  %50 = load i32, ptr %C, align 4, !tbaa !5
  store i32 %50, ptr %D, align 4, !tbaa !5
  %51 = load i32, ptr %B, align 4, !tbaa !5
  %shl60 = shl i32 %51, 30
  %52 = load i32, ptr %B, align 4, !tbaa !5
  %shr61 = lshr i32 %52, 2
  %or62 = or i32 %shl60, %shr61
  store i32 %or62, ptr %C, align 4, !tbaa !5
  %53 = load i32, ptr %A, align 4, !tbaa !5
  store i32 %53, ptr %B, align 4, !tbaa !5
  %54 = load i32, ptr %temp, align 4, !tbaa !5
  store i32 %54, ptr %A, align 4, !tbaa !5
  br label %for.inc63

for.inc63:                                        ; preds = %for.body43
  %55 = load i32, ptr %i, align 4, !tbaa !5
  %inc64 = add nsw i32 %55, 1
  store i32 %inc64, ptr %i, align 4, !tbaa !5
  br label %for.cond40, !llvm.loop !13

for.end65:                                        ; preds = %for.cond40
  store i32 60, ptr %i, align 4, !tbaa !5
  br label %for.cond66

for.cond66:                                       ; preds = %for.inc86, %for.end65
  %56 = load i32, ptr %i, align 4, !tbaa !5
  %cmp67 = icmp slt i32 %56, 80
  br i1 %cmp67, label %for.body69, label %for.end88

for.body69:                                       ; preds = %for.cond66
  %57 = load i32, ptr %A, align 4, !tbaa !5
  %shl70 = shl i32 %57, 5
  %58 = load i32, ptr %A, align 4, !tbaa !5
  %shr71 = lshr i32 %58, 27
  %or72 = or i32 %shl70, %shr71
  %59 = load i32, ptr %B, align 4, !tbaa !5
  %60 = load i32, ptr %C, align 4, !tbaa !5
  %xor73 = xor i32 %59, %60
  %61 = load i32, ptr %D, align 4, !tbaa !5
  %xor74 = xor i32 %xor73, %61
  %add75 = add i32 %or72, %xor74
  %62 = load i32, ptr %E, align 4, !tbaa !5
  %add76 = add i32 %add75, %62
  %63 = load i32, ptr %i, align 4, !tbaa !5
  %idxprom77 = sext i32 %63 to i64
  %arrayidx78 = getelementptr inbounds [80 x i32], ptr %W, i64 0, i64 %idxprom77
  %64 = load i32, ptr %arrayidx78, align 4, !tbaa !5
  %add79 = add i32 %add76, %64
  %conv80 = zext i32 %add79 to i64
  %add81 = add nsw i64 %conv80, 3395469782
  %conv82 = trunc i64 %add81 to i32
  store i32 %conv82, ptr %temp, align 4, !tbaa !5
  %65 = load i32, ptr %D, align 4, !tbaa !5
  store i32 %65, ptr %E, align 4, !tbaa !5
  %66 = load i32, ptr %C, align 4, !tbaa !5
  store i32 %66, ptr %D, align 4, !tbaa !5
  %67 = load i32, ptr %B, align 4, !tbaa !5
  %shl83 = shl i32 %67, 30
  %68 = load i32, ptr %B, align 4, !tbaa !5
  %shr84 = lshr i32 %68, 2
  %or85 = or i32 %shl83, %shr84
  store i32 %or85, ptr %C, align 4, !tbaa !5
  %69 = load i32, ptr %A, align 4, !tbaa !5
  store i32 %69, ptr %B, align 4, !tbaa !5
  %70 = load i32, ptr %temp, align 4, !tbaa !5
  store i32 %70, ptr %A, align 4, !tbaa !5
  br label %for.inc86

for.inc86:                                        ; preds = %for.body69
  %71 = load i32, ptr %i, align 4, !tbaa !5
  %inc87 = add nsw i32 %71, 1
  store i32 %inc87, ptr %i, align 4, !tbaa !5
  br label %for.cond66, !llvm.loop !14

for.end88:                                        ; preds = %for.cond66
  %72 = load i32, ptr %A, align 4, !tbaa !5
  %call = call i32 (ptr, ...) @printf(ptr noundef @.str, i32 noundef %72)
  %73 = load i32, ptr %B, align 4, !tbaa !5
  %call89 = call i32 (ptr, ...) @printf(ptr noundef @.str.1, i32 noundef %73)
  %74 = load i32, ptr %C, align 4, !tbaa !5
  %call90 = call i32 (ptr, ...) @printf(ptr noundef @.str.2, i32 noundef %74)
  %75 = load i32, ptr %D, align 4, !tbaa !5
  %call91 = call i32 (ptr, ...) @printf(ptr noundef @.str.3, i32 noundef %75)
  %76 = load i32, ptr %E, align 4, !tbaa !5
  %call92 = call i32 (ptr, ...) @printf(ptr noundef @.str.4, i32 noundef %76)
  call void @llvm.lifetime.end.p0(i64 4, ptr %i) #3
  call void @llvm.lifetime.end.p0(i64 320, ptr %W) #3
  call void @llvm.lifetime.end.p0(i64 4, ptr %temp) #3
  call void @llvm.lifetime.end.p0(i64 4, ptr %E) #3
  call void @llvm.lifetime.end.p0(i64 4, ptr %D) #3
  call void @llvm.lifetime.end.p0(i64 4, ptr %C) #3
  call void @llvm.lifetime.end.p0(i64 4, ptr %B) #3
  call void @llvm.lifetime.end.p0(i64 4, ptr %A) #3
  ret i32 0
}

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.start.p0(i64 immarg, ptr nocapture) #1

declare i32 @printf(ptr noundef, ...) #2

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.end.p0(i64 immarg, ptr nocapture) #1

attributes #0 = { nounwind uwtable "min-legal-vector-width"="0" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cmov,+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "tune-cpu"="generic" }
attributes #1 = { nocallback nofree nosync nounwind willreturn memory(argmem: readwrite) }
attributes #2 = { "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cmov,+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "tune-cpu"="generic" }
attributes #3 = { nounwind }

!llvm.module.flags = !{!0, !1, !2, !3}
!llvm.ident = !{!4}

!0 = !{i32 1, !"wchar_size", i32 4}
!1 = !{i32 8, !"PIC Level", i32 2}
!2 = !{i32 7, !"PIE Level", i32 2}
!3 = !{i32 7, !"uwtable", i32 2}
!4 = !{!"clang version 17.0.6 (https://github.com/llvm/llvm-project.git 6009708b4367171ccdbf4b5905cb6a803753fe18)"}
!5 = !{!6, !6, i64 0}
!6 = !{!"int", !7, i64 0}
!7 = !{!"omnipotent char", !8, i64 0}
!8 = !{!"Simple C/C++ TBAA"}
!9 = distinct !{!9, !10}
!10 = !{!"llvm.loop.mustprogress"}
!11 = distinct !{!11, !10}
!12 = distinct !{!12, !10}
!13 = distinct !{!13, !10}
!14 = distinct !{!14, !10}
